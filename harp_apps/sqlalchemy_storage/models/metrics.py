from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Repository, contextualize_with_session_if_not_provided


class Metric(Base):
    __tablename__ = "sa_metrics"

    id = mapped_column(Integer(), primary_key=True, unique=True, autoincrement=True)
    name = mapped_column(String(255), unique=True, nullable=False)


class MetricValue(Base):
    __tablename__ = "sa_metric_values"

    metric_id = mapped_column(ForeignKey("sa_metrics.id"), nullable=False, primary_key=True)
    metric: Mapped["Metric"] = relationship()
    created_at = mapped_column(DateTime(), server_default=func.now(), primary_key=True)

    value = mapped_column(Integer())


class MetricValuesRepository(Repository[MetricValue]):
    Type = MetricValue


class MetricsRepository(Repository[Metric]):
    Type = Metric

    def __init__(self, session_factory, /):
        super().__init__(session_factory)
        self.values = MetricValuesRepository(session_factory)

    @contextualize_with_session_if_not_provided
    async def insert_values(self, values: dict, /, session):
        for name, value in values.items():
            metric = await self.find_or_create_one({"name": name}, session=session)
            await self.values.create({"metric_id": metric.id, "value": value}, session=session)