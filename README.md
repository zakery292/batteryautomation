# Version 1.3.0 Working and tested
## Battery Automation for inverters of all makes and models that already intergrate into home assistant and have remote control Confimred working with LUXpower tek with GuyBW's lux integration 

### Fuctions to inlcude the following:  
- Octopus API integration with 6 sensor entitys:   
- Afternoon today rates between 12:00 & 1630  
- Afternoon tomorrow rates between 1200 & 1630  
- All rates available  
- Current import Rate  
- Rates from midnight  
- Rates left till next update  
- Inverter integration providing you have a number of existing sensors  
- Battery Ah to current kWh capacticty this is based on what your inverter get from the BMS
- Battery Charge plan now has three modes which are automaticaly set if you leave the switch turned on Afternoon charging (will pick the best rates deafults to 100%, evening rates between 19:00 & 23:59 deafults to 100% and after midnight) for the short term until version 1.4 comes out i suggest automating the time to turn on the charging switch.
- There are 4 new sensors, these sensors are collalating data from the SOC percentage drop over periods of time and storing them in a SQL database, this data is there to serve two purposes, one to give us a insight into periods of high usage of the battery and react from previous data so the integration can best guess when and how much to charge this is a important step into full autonomy within the integration
- bug fixes and other fun stuff. 

  

### How to setup:
- Add a folder to your custom_components called battery_automation  
- once installed restart home assistant and find the integrations from the devices and services section in your settings  
- Hit add integration and search for battery automation  
- as a minimum you will need your octopus api key and account ID you can get these from your octopus accout   
- if you want to use the battery functions then you will need to add the following:   
- Charge Rate in watts not kW   
- battery SOC sensor  
- Capacity in Ah   
- your charge start time (time. input not input.datetime)  
- your charge end time (time. not input.datetime)   

If your inverter uses input.datetime i cannot confirm this will work it has been desiged to work with the time function, at some point ill add a way to use both. 

All the sensors have the dates stripped out of them to make them more usable in automations so the attributes list currently has: 
- cost
- Date DDMMYYYY
- Start time
- End time
With this you should be able to pick just the part you need ie the date and in standard times not iso or z as the octopus api gives out. this means scripts should work with the times given

The further aim is to get the integration to look at the last 7 days usage create a averge between certain times and ensure capacity during peak usage times almost like AI but im not that cleaver! 

Due to the naming convention used within the integration you might not want to use this and Bottlecap Daves sensor. you might lose the sensors unless you rename them. 
