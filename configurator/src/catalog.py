from dataclasses import dataclass, field
from typing import Any

from exceptions import CatalogError
from util import _read

HTTP_PUSH = 'HttpData-PUSH'
HTTP_PULL = 'HttpData-PULL'

_DATASET_DISTRIBUTION_KEYS = ("dcat:distribution", "distribution")
_DATASET_NAME_KEYS = ("edc:name", "name")
_DATASET_POLICY_KEYS = ("odrl:hasPolicy", "hasPolicy")
_DISTRIBUTION_ACCESS_SERVICE_KEYS = ("dcat:accessService", "accessService")
_DISTRIBUTION_FORMAT_KEYS = ("dct:format", "format")
_ACCESS_SERVICE_ENDPOINT_KEYS = ("dcat:endpointURL", "endpointURL")


def _as_list(value: Any) -> list[Any]:
    """Normalize a value that may be a single dict or a list of dicts into a list."""
    if isinstance(value, dict):
        return [value]
    return value if isinstance(value, list) else []


def _extract_format(distribution: dict[str, Any]) -> str:
    """Read a distribution's transport format, unwrapping the `{'@id': ...}` shape if present."""
    fmt = _read(distribution, *_DISTRIBUTION_FORMAT_KEYS)
    if isinstance(fmt, dict):
        fmt = fmt.get("@id", "")
    return fmt or ""


def _extract_endpoint_url(dataset: dict[str, Any]) -> str:
    """Find the first distribution's access service endpoint URL in a dataset dict."""
    for dist in _as_list(_read(dataset, *_DATASET_DISTRIBUTION_KEYS)):
        if not isinstance(dist, dict):
            continue
        access_service = _read(dist, *_DISTRIBUTION_ACCESS_SERVICE_KEYS)
        if not isinstance(access_service, dict):
            continue
        url = _read(access_service, *_ACCESS_SERVICE_ENDPOINT_KEYS)
        if url:
            return url
    return ""


def _extract_formats(dataset: dict[str, Any]) -> list[str]:
    """Collect all transport formats offered across a dataset's distributions.

    E.g. ['HttpData-PULL', 'HttpData-PUSH', 'ProxyHttpData-PULL'].
    """
    formats = []
    for dist in _as_list(_read(dataset, *_DATASET_DISTRIBUTION_KEYS)):
        if not isinstance(dist, dict):
            continue
        fmt = _extract_format(dist)
        if fmt:
            formats.append(fmt)
    return formats


@dataclass
class Offer:
    """A single catalog offer, wrapping the raw dict returned by the provider's DSP catalog.

    Attributes:
        offer_id: The offer's id (`offerId` in the raw payload), used to negotiate a contract.
        asset_id: The id of the underlying asset/dataset (`assetId` in the raw payload).
        endpoint_url: The DSP endpoint URL to use for contract negotiation / transfer,
            extracted from the first distribution's access service.
        formats: All transport formats offered for this dataset, e.g.
            ['HttpData-PULL', 'HttpData-PUSH'].
        raw: The untouched offer dict as returned by the connector, kept around for any
            fields not explicitly modeled here.
    """

    offer_id: str
    asset_id: str
    endpoint_url: str
    formats: list[str]
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Offer":
        """Build an Offer from a single raw catalog entry."""
        dataset = data.get("dataset", {})
        return cls(
            offer_id=data.get("offerId", ""),
            asset_id=data.get("assetId", ""),
            endpoint_url=_extract_endpoint_url(dataset),
            formats=_extract_formats(dataset),
            raw=data,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Access a raw field on the offer by key, e.g. offer.get('edc:contenttype')."""
        return self.raw.get(key, default)

    @property
    def dataset(self) -> dict[str, Any]:
        """The nested 'dataset' dict describing the asset behind this offer."""
        return self.raw.get("dataset", {})

    @property
    def name(self) -> str:
        """Human-readable dataset name, if provided by the connector."""
        return _read(self.dataset, *_DATASET_NAME_KEYS) or ""

    @property
    def distributions(self) -> list[dict[str, Any]]:
        """List of distributions (transport format + access service) for this dataset."""
        return _as_list(_read(self.dataset, *_DATASET_DISTRIBUTION_KEYS))

    @property
    def supports_pull(self) -> bool:
        """Whether this offer has at least one PULL-capable distribution."""
        return any(fmt.endswith("-PULL") for fmt in self.formats)

    @property
    def supports_push(self) -> bool:
        """Whether this offer has at least one PUSH-capable distribution."""
        return any(fmt.endswith("-PUSH") for fmt in self.formats)

    @property
    def policy(self) -> dict[str, Any]:
        """The ODRL policy matching this offer's id, falling back to the first listed policy."""
        policies = _as_list(_read(self.dataset, *_DATASET_POLICY_KEYS))
        for policy in policies:
            if isinstance(policy, dict) and policy.get("@id") == self.offer_id:
                return policy
        return policies[0] if policies and isinstance(policies[0], dict) else {}

    def stringify(self) -> str:
        """Render a human-readable, multi-line summary of this offer."""
        lines = [
            f"Offer {self.offer_id}",
            f"  Asset ID: {self.asset_id}",
            f"  Name: {self.name or '(unnamed)'}",
            f"  Formats: {', '.join(self.formats) or '(none)'}",
            f"  Endpoint: {self.endpoint_url or '(none)'}",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.stringify()


@dataclass
class Catalog:
    """A provider's catalog, holding the offers returned by a DSP catalog request.

    Attributes:
        offers: The list of Offer objects parsed from the raw catalog response.
        raw: The untouched catalog response dict, kept around for any fields not
            explicitly modeled here.
    """

    offers: list[Offer] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Catalog":
        """Build a Catalog from a raw catalog response dict, extracting its offers."""
        return cls(
            offers=[Offer.from_dict(o) for o in _extract_offers(data)],
            raw=data,
        )

    def __len__(self) -> int:
        return len(self.offers)

    def __iter__(self):
        return iter(self.offers)

    def __getitem__(self, index: int) -> Offer:
        return self.offers[index]

    def select_offer(
            self,
            asset_id: str = "",
            offer_id: str = "",
            index: int = -1,
    ) -> Offer:
        """Select a single offer from the catalog.

        Selectors are checked in order: asset_id, then offer_id, then index.
        If none are given, the first offer in the catalog is returned.

        Args:
            asset_id: Return the offer whose asset id matches exactly.
            offer_id: Return the offer whose offer id matches exactly.
            index: Return the offer at this position in the catalog.

        Raises:
            CatalogError: If no offer matches the given selector, or the
                catalog is empty and no selector was given.
        """
        if asset_id:
            for offer in self.offers:
                if offer.asset_id == asset_id:
                    return offer
            raise CatalogError(f"No offer found for asset id: {asset_id}")

        if offer_id and offer_id >= 0:
            for offer in self.offers:
                if offer.offer_id == offer_id:
                    return offer
            raise CatalogError(f"No offer found for offer id: {offer_id}")

        if index is not None:
            try:
                return self.offers[index]
            except IndexError:
                raise CatalogError(f"No offer found at index: {index}") from None

        if not self.offers:
            raise CatalogError("Provider catalog is empty.")
        return self.offers[0]

    def stringify(self) -> str:
        """Render a human-readable, multi-line summary of the whole catalog."""
        if not self.offers:
            return "Catalog: (empty)"

        header = f"Catalog: {len(self.offers)} offer(s)"
        body = "\n".join(
            f"[{i}] {offer.stringify()}" for i, offer in enumerate(self.offers)
        )
        return f"{header}\n{body}"

    def __str__(self) -> str:
        return self.stringify()


def _extract_offers(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    datasets = _read(catalog, "dcat:dataset", "dataset")
    if datasets is None:
        datasets = []
    if isinstance(datasets, dict):
        datasets = [datasets]

    offers: list[dict[str, Any]] = []
    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue
        asset_id = str(_read(dataset, "@id", "id") or "")
        policies = _read(dataset, "odrl:hasPolicy", "hasPolicy")
        if isinstance(policies, dict):
            policies = [policies]
        if not isinstance(policies, list):
            policies = []
        for policy in policies:
            if not isinstance(policy, dict):
                continue
            if policy.get("@type") and policy.get("@type") not in ["Offer", "odrl:Offer"]:
                continue
            offer_id = str(_read(policy, "@id", "id") or "")
            if asset_id and offer_id:
                offers.append({"assetId": asset_id, "offerId": offer_id, "dataset": dataset})
    return offers
