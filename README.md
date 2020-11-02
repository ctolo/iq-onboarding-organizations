# iq-onboarding-organizations

This script will using the included csv file to add organizations, categories, and applications to the IQ server.  The expected file will have the following columns which should be included as an first row header.

  organizationName,publicId,name,applicationTags

This will require the external project 'requests' which can be installed with the following pip command.

  pip install requests

Overrides for the default params can be included when running the script.  Example:

  python3 iq-onboarding.py -a admin:admin123 -u http://localhost:8070 




