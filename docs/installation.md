# Installation

You need Home Assistant 2026.11 or later (`hacs.json` sets that minimum) and `git` on the Home Assistant host. Home Assistant's container and Home Assistant OS ship it.

[![Open your Home Assistant instance and open this repository in the Home Assistant Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=raine-works&repository=ha-gitops&category=integration)

## From the Home Assistant Marketplace

1. Open the Marketplace (Settings → Marketplace, or the button above).
2. If **GitOps** isn't listed, add `https://github.com/raine-works/ha-gitops` as a custom repository of type **Integration**.
3. Download **GitOps**.
4. Restart Home Assistant.
5. Go on with [Setup](setup.md).

## By hand

Copy `custom_components/gitops` from the repository into `/config/custom_components/gitops`, then restart Home Assistant.

## Updating

Update it from the Marketplace and restart Home Assistant.
