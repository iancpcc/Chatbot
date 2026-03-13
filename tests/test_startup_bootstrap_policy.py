from app.presentation.http import dependencies


def test_reset_state_applies_migrations_and_seed_by_default_in_dev(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("AUTO_APPLY_MIGRATIONS", raising=False)
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)

    calls = {"migrations": 0, "seed": 0}
    monkeypatch.setattr(
        dependencies,
        "apply_migrations",
        lambda: calls.__setitem__("migrations", calls["migrations"] + 1),
    )
    monkeypatch.setattr(
        dependencies,
        "seed_demo_catalog",
        lambda: calls.__setitem__("seed", calls["seed"] + 1),
    )

    dependencies.reset_state()

    assert calls["migrations"] == 1
    assert calls["seed"] == 1


def test_reset_state_skips_migrations_and_seed_by_default_in_prod(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("AUTO_APPLY_MIGRATIONS", raising=False)
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)

    calls = {"migrations": 0, "seed": 0}
    monkeypatch.setattr(
        dependencies,
        "apply_migrations",
        lambda: calls.__setitem__("migrations", calls["migrations"] + 1),
    )
    monkeypatch.setattr(
        dependencies,
        "seed_demo_catalog",
        lambda: calls.__setitem__("seed", calls["seed"] + 1),
    )

    dependencies.reset_state()

    assert calls["migrations"] == 0
    assert calls["seed"] == 0


def test_reset_state_allows_overrides_in_prod(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTO_APPLY_MIGRATIONS", "true")
    monkeypatch.setenv("SEED_DEMO_DATA", "true")

    calls = {"migrations": 0, "seed": 0}
    monkeypatch.setattr(
        dependencies,
        "apply_migrations",
        lambda: calls.__setitem__("migrations", calls["migrations"] + 1),
    )
    monkeypatch.setattr(
        dependencies,
        "seed_demo_catalog",
        lambda: calls.__setitem__("seed", calls["seed"] + 1),
    )

    dependencies.reset_state()

    assert calls["migrations"] == 1
    assert calls["seed"] == 1
