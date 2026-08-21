"""Connector layer: external sources -> raw observations."""

from macropulse.connectors.base import (
    ConnectorError,
    FetchedPoint,
    FetchedSeries,
)
from macropulse.connectors.fred import FredConnector
from macropulse.connectors.ilostat import IlostatConnector
from macropulse.connectors.persist import PersistError, persist_raw_series
from macropulse.connectors.worldbank import WorldBankConnector

__all__ = [
    "ConnectorError",
    "FetchedPoint",
    "FetchedSeries",
    "FredConnector",
    "IlostatConnector",
    "PersistError",
    "WorldBankConnector",
    "persist_raw_series",
]
