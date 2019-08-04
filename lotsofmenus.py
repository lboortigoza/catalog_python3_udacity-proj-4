from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import brand, Base, store, User


engine = create_engine('sqlite:///brandsstore.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="leo", email="lb.ortigoza@gmail.com",
             picture='/picture/leo.jpeg')
session.add(User1)
session.commit()


# Menu for Main China Town
brand1 = brand(user_id=1, name="Bobs", picture="/picture/bobs.jpg")

session.add(brand1)
session.commit()

store2 = store(user_id=1, name="Bobs Jau", description="Loja Bobs localizada na cidade de Jau",
                     price="$25.000,00", brand=brand1)

session.add(store2)
session.commit()


print "added menu items!"