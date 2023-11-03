# Oz Poll

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]

[![Community Forum][forum-shield]][forum]

![AllergyCard][AllergyCard]

## Description

Integrate and visualise Oz allergy forecasts in Home Assistant.

## Installation

It's best if you install and manage this custom component via [HACS](https://hacs.xyz/). HACS opens up a whole world of options so it's really worth setting up if you haven't already.

HACS is also the best way to install and manage another requirement for this project - The custom [Button card](https://github.com/custom-cards/button-card)  is the backbone of the Lovelace "card" for this project (image above). Button Card is really cool of itself too so this is really nice to have anyway. It's only required for the "card visual", not the actual sensor data.

Now for actual installation. Follow any prompts and associated documentation as required. Some steps require restarts. If you get stuck anywhere try a restart.

1. Install [HACS](https://hacs.xyz/)
2. Install [Button card](https://github.com/custom-cards/button-card) (Using HACS installation method is recommended)
3. Install this custom component using HACS (currently uses "custom repository" method). HACS > Integrations > Top right three dots > Custom Repositories: Repository = https://github.com/OkhammahkO/oz-poll, Category = Integration
4. Then configure the sensor (below). After this stop and check your sensor is working ok (showing up in HA). You'll see most of the data is currently stored in the attributes of the sensor (state contains current allergen level).
5. Set up the Lovelace card.
  A. teST 
7. Build yourself some automations and alerts!

## Configuration

```
#In your configuration.yaml
sensor:
  - platform: oz_poll
    url_website: AskOnHAForum
    url_api: AskOnHAForum

```

<!---->

## FAQs
Q: Does this work for location X in Oz?
A: Maybe. Maybe not. Give it a go.

## Limitations
I'm not a programmer and this is both my first HA integration and proper GitHub project. So don't expect a pro set-up, implmentation, and maintenance regime;)
I'll entertain bug and feature requests, but well there will be effort and skill based limits to what I can do.

## Credits

This project was generated from [@oncleben31](https://github.com/oncleben31)'s [Home Assistant Custom Component Cookiecutter](https://github.com/oncleben31/cookiecutter-homeassistant-custom-component) template.

Code template was mainly taken from [@Ludeeus](https://github.com/ludeeus)'s [integration_blueprint][integration_blueprint] template

---

[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[black]: https://github.com/psf/black
[commits-shield]: https://img.shields.io/github/commit-activity/y/OkhammahkO/oz-poll.svg?style=for-the-badge
[commits]: https://github.com/OkhammahkO/oz-poll/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[AllergyCard]: AllergyCard.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/OkhammahkO/oz-poll.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40OkhammahkO-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/OkhammahkO/oz-poll.svg?style=for-the-badge
[releases]: https://github.com/OkhammahkO/oz-poll/releases
[user_profile]: https://github.com/OkhammahkO
