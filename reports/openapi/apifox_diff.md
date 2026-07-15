# OpenAPI Diff Report - shanhai_apifox

- Provider: `apifox`
- Description: 山海智影 Apifox 项目
- Total changes: `14`
- Breaking changes: `0`
- Added operations: `5`
- Removed operations: `0`

## Changes

- `operation_added` `GET /open/video-compose/status`
- `operation_added` `GET /open/voice/list`
- `operation_added` `GET /open/voice/separate/status`
- `operation_added` `POST /open/video-compose/tasks`
- `operation_added` `POST /open/voice/separate`
- `parameter_removed` `POST /open/videots/translate` `query:mode`
- `parameter_removed` `POST /open/videots/translate` `query:target_language`
- `parameter_removed` `POST /open/videots/translate` `query:tos_path`
- `parameter_removed` `POST /open/videots/translate` `query:user_prompt`
- `optional_parameter_added` `POST /open/voice/zeroshot/clone` `query:description`
- `optional_parameter_added` `POST /open/voice/zeroshot/clone` `query:gender`
- `optional_parameter_added` `POST /open/voice/zeroshot/clone` `query:is_public`
- `optional_parameter_added` `POST /open/voice/zeroshot/clone` `query:lang_code`
- `optional_parameter_added` `POST /open/voice/zeroshot/clone` `query:name`
