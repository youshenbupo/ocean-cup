from coze_coding_dev_sdk.database import Base

from typing import Optional
import datetime
import decimal

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Double, Index, Integer, Numeric, PrimaryKeyConstraint, String, Table, Text, text
from sqlalchemy.dialects.postgresql import OID
from sqlalchemy.orm import Mapped, mapped_column

class CommunityComments(Base):
    __tablename__ = 'community_comments'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='community_comments_pkey'),
        Index('community_comments_author_idx', 'author_name'),
        Index('community_comments_post_id_idx', 'post_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False, comment='帖子ID')
    author_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='评论人姓名')
    content: Mapped[str] = mapped_column(Text, nullable=False, comment='评论内容')
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'), comment='点赞数')
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))


class CommunityPosts(Base):
    __tablename__ = 'community_posts'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='community_posts_pkey'),
        Index('community_posts_author_idx', 'author_name'),
        Index('community_posts_category_idx', 'category'),
        Index('community_posts_created_at_idx', 'created_at')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='发帖人姓名')
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment='帖子标题')
    content: Mapped[str] = mapped_column(Text, nullable=False, comment='帖子内容')
    category: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'general'::character varying"), comment='分类: salary/safety/skill/life/general')
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'), comment='浏览次数')
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'), comment='点赞数')
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))


class HealthCheck(Base):
    __tablename__ = 'health_check'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='health_check_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))


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


class SalaryReminders(Base):
    __tablename__ = 'salary_reminders'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='salary_reminders_pkey'),
        Index('salary_reminders_expected_pay_date_idx', 'expected_pay_date'),
        Index('salary_reminders_status_idx', 'status'),
        Index('salary_reminders_worker_name_idx', 'worker_name')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='工友姓名')
    employer_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='雇主/包工头')
    expected_pay_date: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, comment='约定发薪日')
    expected_amount: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment='应发金额')
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'::character varying"), comment='状态: pending/paid/overdue')
    reminder_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, comment='是否已发送提醒')
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    notes: Mapped[Optional[str]] = mapped_column(Text, comment='备注')
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))


class WorkRecords(Base):
    __tablename__ = 'work_records'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='work_records_pkey'),
        Index('work_records_project_name_idx', 'project_name'),
        Index('work_records_work_date_idx', 'work_date'),
        Index('work_records_worker_name_idx', 'worker_name')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='工友姓名')
    work_date: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, comment='工作日期')
    daily_wage: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment='日工资')
    work_hours: Mapped[decimal.Decimal] = mapped_column(Numeric(4, 1), nullable=False, server_default=text("'8'::numeric"), comment='工作小时数')
    is_overtime: Mapped[bool] = mapped_column(Boolean, nullable=False, comment='是否加班')
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('now()'))
    worker_phone: Mapped[Optional[str]] = mapped_column(String(20), comment='联系电话')
    overtime_type: Mapped[Optional[str]] = mapped_column(String(20), comment='加班类型: weekday/weekend/holiday')
    project_name: Mapped[Optional[str]] = mapped_column(String(200), comment='项目名称/工地')
    employer_name: Mapped[Optional[str]] = mapped_column(String(100), comment='雇主/包工头')
    notes: Mapped[Optional[str]] = mapped_column(Text, comment='备注')
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))
