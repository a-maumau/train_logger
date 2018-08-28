☑csv  
☑pickle dict object  
☑tensorboardX  
☑Ggoogle spreasheet  

# Require  
for tensorboradX
require **tensorboardX**.  
  
for google spreadsheet
require **gspread, oauth2client**

# Usage  
You can embed this program in your code.  
see the `test_notification.py` for example.  
Also it is one way to use in pipe.  
For example,  
```
hogehoge | python slack_notify.py
```  
This will make `slack_notify.py` run after `hogehoge` ended.  
I recommend this style because we do not need to embed this in the code.  

# For Lazy People
You can just use `notify.py`  
only you need to do is rewrite the `secret` class for your setting.  

# setup_alias.sh
set up a alias of "python notify.py" to notify.