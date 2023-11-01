# Oz Poll

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![pre-commit][pre-commit-shield]][pre-commit]
[![Black][black-shield]][black]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

[![Community Forum][forum-shield]][forum]

![AllergyCard][AllergyCard]

## Description

Integrate and visualise oz allergy forecasts in Home Assistant.

## Installation

It's best if you install and manage this custom component via [HACS](https://hacs.xyz/). HACS opens up a whole world of options so it's really worth setting up if you haven't already.

HACS is also the best way to install and manage another requirement for this project - The custom [Button card](https://github.com/custom-cards/button-card)  is the backbone of the Lovelace "card" for this project (image above). Button Card is really cool of itself too so this is really nice to have anyway. It's only required for the "card visual", not the actual sensor data.

Some steps require restarts. Follow any prompts as required.

1. Install [HACS](https://hacs.xyz/)
2. Install [Button card](https://github.com/custom-cards/button-card) (Using HACS installation method is recommended)
3. Install this custom component using HACS (current uses custom repository method). HACS > Integrations > Top right three dots > Custom Repositories: Repository = https://github.com/OkhammahkO/oz-poll, Category = Integration
4. Configure the sensor (below). After this stop and check your sensor is working ok. You'll see most of the data is currently stored in the attributes of the sensor (state contains current allergen level).
5. Set up the Lovelace card. XXXXXXXXXXX.
6. Build yourself some automations and alerts! 

## Configuration

```
sensor:
  - platform: oz_poll
    url_website: AskOnHAForum
    url_api: AskOnHAForum

```

<!---->

## FAQs
Q: Does this work for location X?
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
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/OkhammahkO
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/OkhammahkO/oz-poll.svg?style=for-the-badge
[commits]: https://github.com/OkhammahkO/oz-poll/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[AllergyCard]: AllergyCard.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/OkhammahkO/oz-poll.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40OkhammahkO-blue.svg?style=for-the-badge
[pre-commit]: https://github.com/pre-commit/pre-commit
[pre-commit-shield]: https://img.shields.io/badge/pre--commit-enabled-brightgreen?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/OkhammahkO/oz-poll.svg?style=for-the-badge
[releases]: https://github.com/OkhammahkO/oz-poll/releases
[user_profile]: https://github.com/OkhammahkO
