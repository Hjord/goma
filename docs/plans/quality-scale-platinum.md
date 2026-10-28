# Plan: Platinum on the Home Assistant quality scale

Goal: the goma.gg integration meets every rule of the Home Assistant integration quality scale up to Platinum, recorded in `custom_components/goma/quality_scale.yaml` and checked by hassfest.

The rules are taken from `script/hassfest/quality_scale.py` in Home Assistant 2026.10.2.

## Blocker

`dependency-transparency` (Bronze) needs the library source public, released to PyPI, and built and published by CI. The repo stays private until the integration has been tested, so this rule stays `todo` until the release. Everything else can be done now.

## Rules and status

Status: **done** already met, **build** work needed, **exempt** does not apply (reason goes in the yaml), **todo** blocked.

### Bronze

| Rule | Status | Note |
|---|---|---|
| action-setup | exempt | No actions. |
| appropriate-polling | done | Hourly by default, configurable. |
| brands | done | `brand/icon.png`, `brand/icon@2x.png`. |
| common-modules | build | Move the shared device info into a `GomaEntity` base class in `entity.py`. |
| config-flow | done | |
| config-flow-test-coverage | build | Test the `code_not_sent` and `unknown` errors, and `unknown` on the code step. |
| dependency-transparency | todo | See Blocker. |
| docs-actions | exempt | No actions. |
| docs-conditions | exempt | No conditions. |
| docs-high-level-description | done | |
| docs-installation-instructions | done | |
| docs-removal-instructions | build | README section on removing the integration. |
| docs-triggers | exempt | No triggers. |
| entity-event-setup | done | Coordinator listener registered with `async_on_unload`. |
| entity-unique-id | done | |
| has-entity-name | done | |
| runtime-data | done | |
| test-before-configure | done | The flow logs in before creating the entry. |
| test-before-setup | done | `async_config_entry_first_refresh`. |
| unique-config-entry | done | Unique id is the goma user id. |

### Silver

| Rule | Status | Note |
|---|---|---|
| action-exceptions | exempt | No actions. |
| config-entry-unloading | done | |
| docs-configuration-parameters | done | Update interval documented. Recheck wording. |
| docs-installation-parameters | build | Document the email and code fields. |
| entity-unavailable | done | |
| integration-owner | done | `@Hjord`. |
| log-when-unavailable | done | Handled by the coordinator. Confirm with a test. |
| parallel-updates | done | `PARALLEL_UPDATES = 0` on both platforms. |
| reauthentication-flow | done | |
| test-coverage | build | Add pytest-cov to the `ha` group; fail CI under 95 % for `custom_components/goma`. |

### Gold

| Rule | Status | Note |
|---|---|---|
| devices | done | One service device per account, named goma.gg. |
| diagnostics | build | `diagnostics.py`: entry, options and list contents, with email, tokens and user id redacted. |
| discovery | exempt | Cloud service, nothing to discover. |
| discovery-update-info | exempt | Cloud service, nothing to discover. |
| docs-data-update | build | README: how and how often data is read. |
| docs-examples | build | README: automation examples, e.g. a dashboard card and the refresh button. |
| docs-known-limitations | build | README: read-only, email code only, unofficial API. |
| docs-supported-devices | exempt | Service, no devices. |
| docs-supported-functions | build | README: entities and what they show. |
| docs-troubleshooting | build | README: reauth, code not arriving, unreachable. |
| docs-use-cases | build | README: what it is for. |
| dynamic-devices | done | New lists get entities without a reload. |
| entity-category | build | Decide per entity; refresh button likely none. Record the reason. |
| entity-device-class | exempt | No device class fits a list or a refresh button. |
| entity-disabled-by-default | exempt | Every entity is useful by default. |
| entity-translations | done | Button translated; list names come from goma. |
| exception-translations | done | Coordinator errors translated. |
| icon-translations | build | `icons.json` for the button and the lists. |
| reconfiguration-flow | build | Reconfigure step: log in again with a fresh code, same account required. |
| repair-issues | exempt | Nothing a user must repair besides reauth, which has its own flow. |
| stale-devices | build | Remove the entity of a list deleted in goma, instead of leaving it unavailable. Changes current behaviour. |

### Platinum

| Rule | Status | Note |
|---|---|---|
| async-dependency | done | The library is async on httpx. |
| inject-websession | done | The integration passes HA's httpx client. |
| strict-typing | build | Add `py.typed` to the library; run `mypy --strict` on `src/goma` and `custom_components/goma` in CI. |

## Order of work

One branch, one commit per tier, CI green after each:

1. Bronze: `entity.py`, flow error tests, removal docs, `quality_scale.yaml` with every rule.
2. Silver: coverage gate, installation parameter docs.
3. Gold: diagnostics, reconfigure, icons, stale list removal, README sections.
4. Platinum: `py.typed`, mypy strict in CI.

Then install on the test HA with `scripts/install-on-ha.sh` and restart only with permission.

## Done when

- `quality_scale.yaml` lists every rule, and only `dependency-transparency` is `todo`.
- hassfest passes, HA tests pass, coverage of `custom_components/goma` is at least 95 %.
- `mypy --strict` passes on the library and the integration.
- The integration runs on the test HA: lists, refresh button, diagnostics download and reconfigure checked by hand.
