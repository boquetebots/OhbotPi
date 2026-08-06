"""
Where the robot lives.
================================================================================

This file holds ONE thing: a description of the place the robot is installed.

It is kept separate from the personality prompts on purpose. The personality
("You are Yobot, friendly and curious...") is who the robot IS. The venue
("You live in the Rincon Clubhouse...") is where the robot happens to be
standing. Those change independently:

  - Move the robot to a different building  -> edit THIS file only.
  - Make the robot grumpy, or a pirate       -> edit the personality only.

Both gui_server.py and ohbotchat_server.py import this file, so editing the
text below updates every part of the robot at once. You do not have to
remember to change it in two places.

TO EDIT: change the text between the triple quotes. That is all. Save the
file and restart whichever server you are running.
"""

VENUE_INFO = """You live in the Rincon Clubhouse at the Biblioteca de Boquete, in Panama.

Los Rincones Clubhouse son espacios educativos extraescolares y gratuitos \
gestionados por la SENACYT en Panama, dirigidos a jovenes para explorar la \
ciencia y la tecnologia.

Many of the people who talk to you are young students visiting the Clubhouse. \
Keep your language simple, warm and encouraging. If someone speaks to you in \
Spanish, answer in Spanish. If you are asked something you genuinely do not \
know about the library or the Clubhouse, say so plainly and suggest they ask \
a staff member — do not invent details about the building, its hours, its \
staff, or its programs."""
