In order to install dependencies, run the following command in your Python (>3.10) terminal:

pip install -r [PATH TO REQUIREMENTS.TXT]

Replace [PATH TO REQUIREMENTS.TXT] with the directory you extracted the pre-alpha folder to. 
For example:

pip install -r D:\SENTINEL\sentinel-pre-alpha-v.0.2\requirements.txt

From time to time, the port this script uses will be occupied by another process. Usually, this process is not critical to system stability, and you can do "netstat -ano|findstr 8000" in CMD to find out which 
process it is, and then "taskkill /f im PROCCESS_ID" to free up the port.

WARNING!
I bottlenecked this script by applying a max thread limit. Currently, it's at four, but you may change this limit in AHCE.py to whatever your CPU has.
It has also been given authority over a maximum of 80% of available memory.
This script, by default, is extremely resource-intensive, especially during prolonged loads. Exercise caution when modifying the max threads and memory parameters.

Made in collaboration with SENTINEL, a Nous-Hermes based, Azure Cloud Services-powered, 280 million parameter MoRA.

-VN