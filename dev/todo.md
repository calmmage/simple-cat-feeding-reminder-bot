- [ ] run fix_repo
- [ ] launch bot locally
- [ ] launch bot on server


# What I need to do for the first simplest version of the bot to work:


# version 0: dummy-dummy-dummy
- [x] user clicks /start command
- [x] we send user the reminders from there on

# version 1: slightly better
- [x] extend the user setup flow to ask the user when the reminders should be
- [x] extend the reminder functionality to actually wait for user response!
- [x] Send a sample reminder right away!
  - [x] exclude sample reminder from the stats
- [x] add a basic chat handler "This bot doesn't support casual chatting! Commands only: /start, /add_partner, /stats, /full_stats, /stop"
- [x] save users - user data
  - [x] dev command: see saved users - admin-only (do I have such feature in botspot?) Should be a simple filter though
- [x] Find some easy way to specify and support time zones
  - [x] use time zone to schedule - check that. (log) 
  - [x] check tz is saved to user
  - [x] log true time - and in how many hours till the next reminder
  - [x] show times of day in schedule selector
  - [ ] if timezone is missing - run the timezone setup flow, not fallback to default
- [ ] on startup - load and activate user schedules
- [ ] Find a simple way to deploy the bot
  - [ ] Dockerfile
  - [ ] Docker compose
  - [ ] ...
- [ ] simple way to add partner
  - [ ] cancel the reminder if other partner has already fed
  - [ ] create reminders for partner as well
  - [ ] on startup - load and activate partner schedules
- [x] log feedings and add /stats and /full_stats commands
  - [ ] bonus: random job (end of week?) for weekly summary
  - [ ] bonus: admin-only command to see all usage
  - [ ] /stop command

Next steps
- [ ] reset_reminders command
- [x] 'cancel' button for the schedule setup flow
- [ ] setup timezone
  - [ ] location
  - [ ] string
  - [ ] current time
- [ ] add a basic chat handler: 

Feature 2: Specify a partner
- find a simple way to specify a partner


# version 2: use the database
- [ ] users in the database
- [ ] save schedule in the database
- [ ] save ... log + photos in the database

# version 3: add support for other people responsible for feeding the cat


# version 4: sending the picture. forward picture to other users


# version 5: 