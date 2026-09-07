"""Vehicle (kendaraan) ORM model."""
from sqlalchemy import Column, Integer, String, Boolean, CheckConstraint
from api.models.base import Base, TimestampMixin


class Vehicle(TimestampMixin, Base):
    __tablename__ = "kendaraan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plat = Column(String(15), unique=True, nullable=False, index=True)
    nama_pemilik = Column(String(100))
    jabatan = Column(String(1), CheckConstraint("jabatan IN ('D', 'W', 'S')"), nullable=False)
    cluster_hak = Column(String(10), CheckConstraint("cluster_hak IN ('Merah', 'Orange')"), nullable=False)
    aktif = Column(Boolean, default=True, nullable=False)

    @property
    def cluster(self) -> str:
        """Compatibility property for the API response schema."""
        return self.cluster_hak

    @property
    def status(self) -> str:
        """Human-readable active status for the API response schema."""
        return "aktif" if self.aktif else "nonaktif"
