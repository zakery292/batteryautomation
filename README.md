Battery Automation for inverters of all makes and models that already intergrate into home assistant and have remote control. 

At the moment the only working fucntioality of the integration is the octopus api which provides the following sesnors:
- This afternoons slots between 12:00 & 16:00
- Tomorrow Afternoons slots between 12:00 & 16:00
- Tonights slots from 00:00 till 08:00
- All slots from today till tomorrow

All the sensors have the dates stripped out of them to make them more usable in automations so the attributes list currently has: 
- cost
- Date DDMMYYYY
- Start time
- End time
With this you should be able to pick just the part you need ie the date and in standard times not iso or z as the octopus api gives out. this means scripts should work with the times given

The integration now asks for optional inputs for battery charge state, battery capacity ah state, battery charge start and end times
Currently the integration will calculate the actual kwh of the batteries based on a 50v system but this can be amended to include a range of voltages 

Can and will now create a dynamic charge plan updated every 30 mins based upon battery level, will select slots and produce a plan in time order to charge with a estimated cost based upon your charge rate. 

Will now send to inverter and you can turn off the charge plan so it wont run if you dont want it too, next steps are to offer the best afternoon rates and evening rates till midnight via a choice of slots eg if you notice there are three super cheap slots
before midnight select three itll pick the cheapest three and then itll send it for you, eventually i want the charge plan to be dynamic untill midnight so eg if you @ midnight the charge is 40% but you want 70% overall itll sort the difference and charge

then moving forward solcast integration amongst other things.

the integration will work with LUX inverters using GuyBWs integration but should work with others if they are using time. for the sending of the times to the inverter not input.datetime but this can be amended in a future versions if both are required. 

The further aim is to get the integration to look at the last 7 days usage create a averge between certain times and ensure capacity during peak usage times almost like AI but im not that cleaver! 

The octopus integration has been moved from local api calls for each sensor to one global dictionary this means the data will be easily accessable for all future addons. 
Ah to kWh has now been moved from the sensor file to the __init__ file in order to creat a global variable that we can access for other logic

to install just copy the contents to your custom_components folder, with the folder name battery_automation
Restart HA and then enter your API key and account number for octopus, this will find your tariff and then show you the rates for you personally. 

Due to the naming convention used within the integration you might not want to use this and Bottlecap Daves sensor. you might lose the sensors unless you rename them. 
