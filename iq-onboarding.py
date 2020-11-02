#!/usr/bin/python3

import csv
import argparse
import subprocess
import json
import requests

iq_url, iq_auth, iq_session, default_org = "", "", "",""
categories, organizations, applications = [], [], []

def getArguments():
    global iq_url, iq_session, iq_auth
    parser = argparse.ArgumentParser(description='Onboarding Organizations and Applications')
    parser.add_argument('-u', '--url', help='', default="http://localhost:8070", required=False)
    parser.add_argument('-a', '--auth', help='', default="admin:admin123", required=False)
    parser.add_argument('-f','--file_name', default="sample_import.csv", required=False)
    parser.add_argument('-o','--default_org', default="Sandbox Organization", required=False)

    args = vars(parser.parse_args())
    iq_url = args["url"]
    creds = args["auth"].split(":")
    iq_session = requests.Session()

    # load user credentials, recommended to use admin account to avoid onboarding errors.
    iq_auth = requests.auth.HTTPBasicAuth(creds[0], creds[1])    
    iq_session.auth = iq_auth
    return args

def main():
    global default_org
    # grab defaults or args passed into script.
    args = getArguments()
    file_name = args["file_name"]
    default_org = args["default_org"]

    # store current applications, categories, and organizations
    set_categories()
    set_organizations()
    set_applications()

    apps = get_load_file(file_name)
    print("-"*40,"start","-"*40)
    print(f"File has {len(apps)} apps to load.")

    for app in apps:
        if not app['publicId']:
            print(f'No publicId {app}')

        found = check_application(app)

        # If app doesn't exist and the name has not been used then add the app.
        if found is None and name_available(app['name']):
            new_app = add_application(app)
            if new_app is not None:
                print(f"added {app['publicId']} to {app['organizationName']}: {new_app['id']}")
                applications.append(new_app)
        else:
            print(f"skipping {app['publicId']}")

    print("-"*40,"fin","-"*40)

    #----------------------------------------------------------------------
#--------------------------------------------------------------------------
def pp(c):
    # testing json output to console
    print(json.dumps(c, indent=4))

def handle_resp(resp, root=""):
    #normalize api call responses
    if resp.status_code != 200:
        print( resp )
        return None
    node =  resp.json()
    if root in node:
        node = node[root]
    if node is None or len(node) == 0:
        return None
    return node


def get_url(url, root=""):
    #common get call
    resp = iq_session.get(url, auth=iq_auth)
    return handle_resp(resp, root)


def post_url(url, params, root=""):
    #common post call
    resp = iq_session.post(url, json=params, auth=iq_auth)
    return handle_resp(resp, root)

#--------------------------------------------------------------------------

def set_applications():
    global applications
    url = f'{iq_url}/api/v2/applications'
    applications = get_url(url, "applications")


def set_organizations():
    global organizations
    url = f'{iq_url}/api/v2/organizations'
    organizations = get_url(url, "organizations")


def check_organization(name):
    ret = ''
    for c in organizations:
        if name in c['name']: ret = c['id']
    if len(ret) == 0: 
        ret = add_organization(name)
    if len(ret) > 0:
        return ret
    else:
        return None


def check_application(new_app):
    # name is required, default to PublicId
    if not new_app['name']:  
        new_app['name'] = new_app['publicId']

    # org is required, default to default_org
    if not new_app['organizationName']: 
        new_app['organizationName'] = default_org

    # Look to see if new app already exists
    for app in applications:
        if app['publicId'] == new_app["publicId"]:
            return app
    return None

def name_available(name):
    for app in applications:
        if app['name'] == name:
            return False
    return True


def add_application(app):
    data = {
        "publicId": app["publicId"], "name": app["name"],
        "organizationId": check_organization(app['organizationName']),
        "applicationTags": fetch_categories(app['applicationTags'] )
    }
    return post_url(f'{iq_url}/api/v2/applications', data)


def add_organization(org_name):
    data = {"name": org_name}
    url = f'{iq_url}/api/v2/organizations'
    resp = post_url(url, data)
    if resp is not None:
        organizations.append(resp)
        return resp['id']
    return ''

def fetch_categories(app_tag):
    ret = []
    for tag in app_tag:
        tag_ = check_category(tag)
        if not tag_ is None:
            ret.append(tag_)
    return ret


def check_category(name):
    ret = ''
    if len(name) == 0: return None 
    for c in categories:
        if name in c['name']: ret = c['id']
    if len(ret) == 0:
        ret = add_category(name)
    if len(ret) > 0:
        return {'tagId': ret}
    return None


def set_categories():
    global categories
    # using categories from root organization.
    url = f'{iq_url}/api/v2/applicationCategories/organization/ROOT_ORGANIZATION_ID'
    categories = get_url(url)


def add_category(name):
    global categories
    url = f'{iq_url}/api/v2/applicationCategories/organization/ROOT_ORGANIZATION_ID'
    data = {"name": name,"color": "dark-blue", "description": name}
    resp = post_url(url, data)
    if resp is not None:
        categories.append(resp)
        return resp['id']
    return ''


def get_load_file(file_name):
    # loading csv file and checking for required headers. 
    container, missing, required = [],[],['organizationName', 'publicId', 'name', 'applicationTags']
    print('-'*60)
    print("checking import file for required columns")
    print(required)
    print('-'*60)
    
    with open(file_name, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for r in required:
            if r not in reader.fieldnames:
                missing.append(r)
        if len(missing) > 0:
            print(f"Import File is missing fields {missing}.")
            exit(1)
        for row in reader:
            row['applicationTags'] = row['applicationTags'].split(',')
            container.append(row)
    return container


#--------------------------------------------------------------------
if __name__ == "__main__":
    main()
