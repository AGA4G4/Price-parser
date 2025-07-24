This piece of code processes the prices of a message which was saved by another c++ server in my RLM repostiroy and it's name is [received_messages.txt].  
Attention: For this code to work you must have a file named like the one said above next to your code, because the file is the codes input.  
The code functions like this:  
Reads the text => Extracts date and prices of variables => compares them to previous data to determine it's candle (Whether the price has gone up, down or stayed consistant) => Creates a log and output.json  
The purpose of logs folder is for comparing the prices of the very day with it's previous day. 
