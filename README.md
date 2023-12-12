
# france-embassy-notifier
It's an notifier of the Ambsassade de France (consulat.gouv.fr/es/ambassade-de-france-a-bogota/appointment) for available appointment to get a Visa for students, assistants de langue and VVT (Visa Vacances Travail). 

## Prerequisites 
- API Token BOT from telegram for noitifications (optional)
- Python v3 installed (for running the script). 

### AWS
- Docker installed (to create the image)
- AWS Credentials configured 
- Serverless framework installed (to deploy the image)

## Executing the script

### Local
Install the required python packages: pip install -r requirements.txt
Simply run python -c "import setup; setup.as_loop()"

### AWS
Do not need to install requirements.txt. I think you must install just 'requests' module with pip install 'requests'
Later, run python -c "import setup; setup.as_lambda_function()"
In case you want to stop or delete the function run sls delete
That's it!

## Acknowledgement
- Inspired in the work of @uxDaniel and @dvalbuena1 in the USA Visa Rescheduler. 
- [Original Repo](https://github.com/uxDaniel/visa_rescheduler) and [Fork](https://github.com/dvalbuena1/visa_rescheduler_aws)

