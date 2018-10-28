# Item Catalog
An application that provides a list of 
items within a variety of categories as well as 
provide a user registration and authentication system. 
Registered users will have the ability to post, edit and
delete their own items.

## Setup:

* Clone this repo
* Install: 
  * Flask
  * SQLAlchemy

1. Open terminal and change directory into folder with cloned repository
2. Run db_setup.py: `python db_setup.py`
3. Run db_seed.py: `python db_seed.py`
4. Run app.py to start web server: `python app.py`
5. Open browser: [http://localhost:5000/category/](http://localhost:5000/category/)

## Features:
* Login/Logout with Google account.
* CRUD Operations
* JSON Endpoints
    * append /json to any endpoint
    
## Endpoints:
* Category list: [http://localhost:5000/category](http://localhost:5000/category)
* Specific category's items: [http://localhost:5000/category/\<category_id\>](http://localhost:5000/category/1)
* Specific item information: [http://localhost:5000/category/\<category_id\>/\<item_id\>](http://localhost:5000/category/1/1)
