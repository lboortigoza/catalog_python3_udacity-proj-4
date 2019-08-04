#!/usr/bin/env python
from flask import (Flask,
                   render_template,
                   request,
                   redirect,
                   url_for,
                   flash,
                   jsonify)
from flask import session as login_session
from flask import make_response

from database_setup import Base, Brand, Store, User
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker

import random
import string
import httplib2
import json
import requests

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

app = Flask(__name__)

# Load the Google Login API Client ID
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu app"

# Create a database session and connect to the database
engine = create_engine('sqlite:///brandsstore.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token


@app.route('/login')
def showLogin():
    # Remove Oauth
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Connect to the Google Login oAuth method
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is connected'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data.get('name', '')
    login_session['picture'] = data.get('picture', '')
    login_session['email'] = data.get('email', '')

    # See if a user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    # Show a welcome message upon successful login
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;\
                           border-radius:150px;-webkit-border-radius:\
                           150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one_or_none()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except Exception:
        return None


# Disconnect - Revoke current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username'].encode('utf-8').strip()

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token  # noqa
    print(url)
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('Brands'))
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect - Disconnects and redirects to index
@app.route('/disconnect')
@app.route('/Brands/disconnect')
def disconnect():
    gdisconnect()
    return redirect(url_for('Brands'))


# JSON APIs to view Brand Information
@app.route('/Brands/<int:brand_id>/menu/JSON')
def brandMenuJSON(brand_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    items = session.query(Store).filter_by(
        brand_id=brand_id).all()
    return jsonify(stores=[i.serialize for i in items])


# JSON APIs to view Brand and Store specifically Information
@app.route('/Brands/<int:brand_id>/menu/<int:menu_id>/JSON')
def storeJSON(brand_id, menu_id):
    Menu_Item = session.query(Store).filter_by(id=menu_id).one()
    return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/Brands/JSON')
def BrandsJSON():
    Brands = session.query(Brand).all()
    return jsonify(Brands=[r.serialize for r in Brands])


# Show all Brands
@app.route('/')
@app.route('/Brands/')
def Brands():
    Brands = session.query(Brand).order_by(asc(Brand.name))
    print(Brands)
    # Remove Oauth
    if 'username' not in login_session:
        return render_template('publicBrandslist.html',
                               Brands=Brands)
    else:
        return render_template('Brandslist.html', Brands=Brands,
                               loginname=login_session)


# Create a new Brand
@app.route('/Brand/new/', methods=['GET', 'POST'])
def newBrand():
    # Remove Oauth
    if 'username' not in login_session:
        return redirect('/login')

    print(login_session)
    if request.method == 'POST':
        # Remove Oauth
        newBrand = Brand(name=request.form['name'],
                         user_id=login_session['user_id'])
        session.add(newBrand)
        flash('New Brand %s Successfully Created' % newBrand.name)
        session.commit()
        return redirect(url_for('Brands'))
    else:
        return render_template('newBrand.html')


# Edit brand_id name
@app.route('/Brand/<int:brand_id>/edit/', methods=['GET', 'POST'])
def editBrand(brand_id):
    # Remove Oauth
    if 'username' not in login_session:
        return redirect('/login')
    editedBrand = session.query(Brand)\
        .filter_by(id=brand_id).one()
    # Remove Oauth
    # if editedBrand.user_id != login_session['user_id']:
    ###
    if editedBrand.user_id != login_session['user_id']:
        return "<script>function myFunction()\
            {alert('You are not authorized to edit this Brand.\
            Please create your own Brand in order to edit.');}\
            </script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedBrand.name = request.form['name']
            flash('Brand Successfully Edited %s' % editedBrand.name)
            return redirect(url_for('Brands'))
    else:
        return render_template('editBrand.html',
                               brand=editedBrand)


# Delete a Brand
@app.route('/Brand/<int:brand_id>/delete/', methods=['GET', 'POST'])
def deleteBrand(brand_id):
    # Remove Oauth
    if 'username' not in login_session:
        return redirect('/login')
    BrandToDelete = session.query(Brand)\
        .filter_by(id=brand_id).one()
    # Remove Oauth
    # if BrandToDelete.user_id != login_session['user_id']:
    if BrandToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction()\
            {alert('You are not authorized to delete this Brand.\
            Please create your own Brand in order to delete.');}\
            </script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(BrandToDelete)
        flash('%s Successfully Deleted' % BrandToDelete.name)
        session.commit()
        return redirect(url_for('Brands',
                                brand_id=brand_id))
    else:
        return render_template('deleteBrand.html',
                               brand=BrandToDelete)


# Display the Menu Items
@app.route('/Brands/<int:brand_id>/menu')
def brandMenu(brand_id):
    brand = session.query(Brand).filter_by(id=brand_id).one()
    creator = getUserInfo(brand.user_id)
    items = session.query(Store).filter_by(brand_id=brand.id)
    # Remove Oauth
    if 'username' not in login_session\
            or creator.id != login_session['user_id']:
        return render_template('publicmenu.html', items=items,
                               brand=brand, creator=creator)
    else:
        return render_template('menu.html',
                               brand=brand,
                               items=items,
                               brand_id=brand_id,
                               creator=creator)


# Create new Menu Item
@app.route('/Brand/<int:brand_id>/new/', methods=['GET', 'POST'])
def newStore(brand_id):
    # Remove Oauth
    if 'username' not in login_session:
        return redirect('/login')

    brand = session.query(Brand).filter_by(id=brand_id).one()
    print(brand.name)
    if request.method == 'POST':
        newItem = Store(name=request.form['name'],
                        description=request.form['description'],
                        price=request.form['price'],
                        brand_id=brand_id,
                        user_id=brand.user_id)
        session.add(newItem)
        session.commit()
        print("new store item created!")
        flash("new store item created!")
        print()
        return redirect(url_for('brandMenu', brand_id=brand_id))
    else:
        return render_template('newstore.html', brand_id=brand_id)


# Edit a menu item
@app.route('/Brands/<int:brand_id>/<int:menu_id>/edit',
           methods=['GET', 'POST'])
def editStore(brand_id, menu_id):
    # Remove Oauth
    if 'username' not in login_session:
        return redirect('/login')
    brand = session.query(Brand).filter_by(id=brand_id).one()
    editedItem = session.query(Store).filter_by(id=menu_id).one()

    if editedItem.user_id != login_session['user_id']:
        return "<script>function myFunction()\
        {alert('You are not authorized to edit this Store.\
        Please create your own Store in order to edit.');}\
        </script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash("menu item edited!")
        return redirect(url_for('brandMenu', brand_id=brand_id))
    else:
        return render_template('editstore.html',
                               brand_id=brand_id,
                               menu_id=menu_id, item=editedItem)


# Delete a menu item
@app.route('/Brands/<int:brand_id>/<int:menu_id>/delete',
           methods=['GET', 'POST'])
def deleteStore(brand_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    brand = session.query(Brand).filter_by(id=brand_id).one()
    itemToDelete = session.query(Store).filter_by(id=menu_id).one()
    if itemToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction()\
        {alert('You are not authorized to edit this Store.\
        Please create your own Store in order to delete.');}\
        </script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("menu item deleted!")
        return redirect(url_for('brandMenu', brand_id=brand_id))
    else:
        return render_template('deletestore.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000, threaded=False)
