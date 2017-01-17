
import urllib
import urllib.request as urllib2

# url = "http://localhost:3000/getEssays"
url = "http://localhost:8080"
request = urllib2.Request(url)
response = urllib2.urlopen(request)
results = response.read().decode('utf-8')

with open('./essays.txt','w') as f:
	f.write(results)
# print(response)
