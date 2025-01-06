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
- [ ] save users - user data
  - [ ] dev command: see saved users - admin-only (do I have such feature in botspot?) Should be a simple filter thoug
- [ ] Find some easy way to specify and support time zones
- [ ] Find a simple way to deploy the bot
  - [ ] Dockerfile
  - [ ] Docker compose
  - [ ] ...
- [ ] simple way to add partner
  - [ ] cancel the reminder if other partner has already fed
- [ ] log feedings and add /stats and /full_stats commands
  - [ ] bonus: random job (end of week?) for weekly summary
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