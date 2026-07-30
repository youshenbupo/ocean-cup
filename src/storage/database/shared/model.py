from coze_coding_dev_sdk.database import Base

from typing import Optional
import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Double, Index, Integer, Numeric, PrimaryKeyConstraint, String, Table, Text, text, func
from sqlalchemy.dialects.postgresql import OID
from sqlalchemy.orm import Mapped, mapped_column

class HealthCheck(Base):
    __tablename__ = 'health_check'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='health_check_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))


class WorkRecord(Base):
    """工时记录表 - 薪资管家功能"""
    __tablename__ = 'work_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="工友姓名")
    worker_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="联系电话")
    work_date: Mapped[datetime.date] = mapped_column(DateTime(timezone=True), nullable=False, comment="工作日期")
    daily_wage: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False, comment="日工资")
    work_hours: Mapped[float] = mapped_column(Numeric(precision=4, scale=1), nullable=False, server_default="8", comment="工作小时数")
    is_overtime: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否加班")
    overtime_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="加班类型: weekday/weekend/holiday")
    project_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="项目名称/工地")
    employer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="雇主/包工头")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("work_records_worker_name_idx", "worker_name"),
        Index("work_records_work_date_idx", "work_date"),
        Index("work_records_project_name_idx", "project_name"),
    )


class SalaryReminder(Base):
    """薪资提醒表 - 欠薪预警功能"""
    __tablename__ = 'salary_reminders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="工友姓名")
    employer_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="雇主/包工头")
    expected_pay_date: Mapped[datetime.date] = mapped_column(DateTime(timezone=True), nullable=False, comment="约定发薪日")
    expected_amount: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False, comment="应发金额")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending", comment="状态: pending/paid/overdue")
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已发送提醒")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("salary_reminders_worker_name_idx", "worker_name"),
        Index("salary_reminders_status_idx", "status"),
        Index("salary_reminders_expected_pay_date_idx", "expected_pay_date"),
    )


t_pg_stat_statements = Table(
    'pg_stat_statements', Base.metadata,
    Column('userid', OID),
    Column('dbid', OID),
    Column('toplevel', Boolean),
    Column('queryid', BigInteger),
    Column('query', Text),
    Column('plans', BigInteger),
    Column('total_plan_time', Double(53)),
    Column('min_plan_time', Double(53)),
    Column('max_plan_time', Double(53)),
    Column('mean_plan_time', Double(53)),
    Column('stddev_plan_time', Double(53)),
    Column('calls', BigInteger),
    Column('total_exec_time', Double(53)),
    Column('min_exec_time', Double(53)),
    Column('max_exec_time', Double(53)),
    Column('mean_exec_time', Double(53)),
    Column('stddev_exec_time', Double(53)),
    Column('rows', BigInteger),
    Column('shared_blks_hit', BigInteger),
    Column('shared_blks_read', BigInteger),
    Column('shared_blks_dirtied', BigInteger),
    Column('shared_blks_written', BigInteger),
    Column('local_blks_hit', BigInteger),
    Column('local_blks_read', BigInteger),
    Column('local_blks_dirtied', BigInteger),
    Column('local_blks_written', BigInteger),
    Column('temp_blks_read', BigInteger),
    Column('temp_blks_written', BigInteger),
    Column('shared_blk_read_time', Double(53)),
    Column('shared_blk_write_time', Double(53)),
    Column('local_blk_read_time', Double(53)),
    Column('local_blk_write_time', Double(53)),
    Column('temp_blk_read_time', Double(53)),
    Column('temp_blk_write_time', Double(53)),
    Column('wal_records', BigInteger),
    Column('wal_fpi', BigInteger),
    Column('wal_bytes', Numeric),
    Column('jit_functions', BigInteger),
    Column('jit_generation_time', Double(53)),
    Column('jit_inlining_count', BigInteger),
    Column('jit_inlining_time', Double(53)),
    Column('jit_optimization_count', BigInteger),
    Column('jit_optimization_time', Double(53)),
    Column('jit_emission_count', BigInteger),
    Column('jit_emission_time', Double(53)),
    Column('jit_deform_count', BigInteger),
    Column('jit_deform_time', Double(53)),
    Column('stats_since', DateTime(True)),
    Column('minmax_stats_since', DateTime(True))
)


t_pg_stat_statements_info = Table(
    'pg_stat_statements_info', Base.metadata,
    Column('dealloc', BigInteger),
    Column('stats_reset', DateTime(True))
)
