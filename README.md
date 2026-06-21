# ElysianRealmAssistant

ElysianRealmAssistant is a LangBot plugin for Honkai Impact 3rd Elysian Realm queries. It replies with current recommendation charts, character guide images, or alias lists based on user messages.

## Installation

Install this plugin by following the [LangBot plugin installation guide](https://docs.langbot.app/en/plugin/plugin-intro#installing-plugins)

## Usage

### `乐土推荐`

Returns Elysian Realm recommendation charts ordered by recommendation priority. Add a number to request a specific chart, for example `乐土推荐2`.

![image](https://github.com/user-attachments/assets/9c30491c-8ad7-4aed-acfe-8ef29dab8dde)

![image](https://github.com/user-attachments/assets/ea3ef8ea-ae9c-44c8-874b-117cc2707bef)

### Character Guide Search

Send a character-related Elysian Realm query to fetch the matching guide image.

![image](https://github.com/user-attachments/assets/4fea1c40-a954-4be9-baf0-6d37173dc68c)

### `乐土list`

Use `乐土list` to show the full alias list, or prefix it with a keyword to search matching entries.

![image](https://github.com/user-attachments/assets/980d35a1-cf88-498a-bdae-1b88d356e894)

### Error Handling

When a guide cannot be found or an image cannot be sent, the plugin returns an error message instead of silently failing.

![image](https://github.com/user-attachments/assets/96a3dc7b-9696-4fd0-bad0-fa46928a1a73)

![image](https://github.com/user-attachments/assets/90aacfd5-f46a-45b2-aa6c-28289435623c)

### Character Name Matching

The character-name part of a guide query matches up to five characters.

![image](https://github.com/user-attachments/assets/9bc12c87-4ce0-426d-aa75-20c9b125f0ac)

## Changelog

### v1.7.0

Refactored the `乐土推荐` API handling to reduce dependence on upstream response details.

### v1.5.0

Added image caching for MiHoYo BBS images and reused a single session during cache warm-up to improve download performance.

### v1.2.0

Added a temporary workaround for intermittent image-send failures observed in the bot framework.

![image](https://github.com/user-attachments/assets/1e6cbd03-cb9c-4ee0-b249-7d80363cb71a)

![image](https://github.com/user-attachments/assets/978c7dd8-e5b7-4d77-810e-a371ceceed53)
