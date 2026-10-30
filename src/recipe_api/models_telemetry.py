from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class TelemetryBase(DeclarativeBase):
    """Base class for the Recipe DB tables."""


class Session(TelemetryBase):
    """Represents a telemetry session."""

    __tablename__ = "Sessions"
    __table_args__ = {"info": {"bind_key": "TelemetryDB"}}

    session_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    app_version: Mapped[str] = mapped_column(String(20), nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)

    events: Mapped[list["TelemetryEvent"]] = relationship(back_populates="session")


class TelemetryEventsTable(TelemetryBase):
    """Represents the telemetry events table."""

    __tablename__ = "Telemetry_Events_Table"
    __table_args__ = {"info": {"bind_key": "TelemetryDB"}}

    event_type_id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class TelemetryEvent(TelemetryBase):
    """Represents a telemetry event."""

    __tablename__ = "Telemetry_Events"
    __table_args__ = (
        CheckConstraint("ISJSON(event_data) = 1", name="CK_Telemetry_Events_Data"),
        {"info": {"bind_key": "TelemetryDB"}},
    )

    event_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("Sessions.session_id"), nullable=False)
    event_type_id: Mapped[int] = mapped_column(
        ForeignKey("Telemetry_Events_Table.event_type_id"), nullable=False
    )
    event_data: Mapped[str] = mapped_column(Text, nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    session: Mapped["Session"] = relationship(back_populates="events")
