- [x] ask for a picture and recognize it!

- [x] reload schedules from db on bot restart 
- [ ] add num_retries to the ... reminders

- [ ] add new settings menu to config stuff
  - [ ] num retries
  - [ ] time between retries
- [ ] record feeding time - structured output to parse from the bot
- [ ] analyze 'yes' or 'no' in the response to the reminder
  - if yes -> record
  - if no -> ... ? retry, ... 
- [x] if in chat message "GMT+..." regexp -> ... treat as timezone setter
- [x] /stop command
- [x] bugfix issue when incorrect response to /start / /setup command
- [ ] if /command -> always react correctly? Need to check my implementation of ask_user... (capture state)

- [ ] well, add partner feature

- [x] bugfix chat message formatting


1. Move handlers to appropriate files:
- [x] start.py:
  - [x] command_start_handler
- [x] schedule.py:
  - [x] setup_schedule
  - [x] schedule_reminder
  - [x] clear_user_schedule
  - [x] stop_command (new)
- [x] feeding.py:
  - [x] send_reminder
  - [x] register_meal
- [x] settings.py:
  - [x] timezone_setup
  - [x] setup_timezone
- [x] info.py:
  - [x] help_command
  - [x] stats_command
  - [x] full_stats_command
- [x] common.py:
  - [x] handle_messages (fallback)
