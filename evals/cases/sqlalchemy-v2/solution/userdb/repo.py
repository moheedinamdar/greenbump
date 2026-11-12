from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select, text

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(50), nullable=False),
    Column("email", String(100), nullable=False),
)


def make_engine(url="sqlite://"):
    engine = create_engine(url)
    metadata.create_all(engine)
    return engine


def add_user(engine, name, email):
    with engine.begin() as conn:
        conn.execute(users.insert().values(name=name, email=email))


def user_names(engine):
    with engine.connect() as conn:
        rows = conn.execute(select(users.c.name).order_by(users.c.name))
        return [row[0] for row in rows]


def count_users(engine):
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
