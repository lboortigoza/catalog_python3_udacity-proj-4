import sys
import os

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

# class for the User table
class User(Base):
    """
    Registered user information is stored in db
    """
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


# class for the brand table
class Brand(Base):
    """
    brand information is stored in db
    """
    __tablename__ = 'brand'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)    

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    # To send JSON objects in a serializable format
    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,            
        }


# class for stores table
class Store(Base):
    """
    Store in Brands are stored in db
    """
    __tablename__ = 'store'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)    
    description = Column(String(250))
    price = Column(String(8))

    brand_id = Column(Integer, ForeignKey('brand.id'))
    brand = relationship(Brand)

    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    # To send JSON objects in a serializable format
    @property
    def serialize(self):

        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,            
        }

engine = create_engine('sqlite:///brandsstore.db')

Base.metadata.create_all(engine)
