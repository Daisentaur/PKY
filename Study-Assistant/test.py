import requests

url = "http://localhost:5000/upload"
with open('1050-text-s.pdf', 'rb') as f:
    response = requests.post(url, 
        files={'files': f},
        data={'keywords': 'sequence,geometric,mathematics'}
    )
print(response.json())