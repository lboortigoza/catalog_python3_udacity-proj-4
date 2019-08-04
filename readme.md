# Project 4 from Udacity
A Web App that creat Brands and Store. The user can Create, Read, Update and Delete Brands and Stores. 

## Features:
- For Create, read, update and delete, need authorization.

### Requirements
* Python 2.7
* Vagrant
* VirtualBox
* sqlalchemy
* Google Chrome 

### How to Run

1. Lunch vagrant 
	- Vagrant Up
	- Vagrant SSH

2. Go to directory

3. Initialize project
   - Python project-1.py
   
4. Open the browser and go to http://localhost:5000

5. Enjoy


### JSON endpoints
# JSON APIs to view Brand Information
/Brands/<int:brand_id>/menu/JSON

# JSON APIs to view Brand and Store specifically Information
/Brands/<int:brand_id>/menu/<int:menu_id>/JSON

# Json All Brands
/Brands/JSON