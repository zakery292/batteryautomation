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
The charging logic is a work in progress the sensor is there but the charge plan from midnight doesnt calculate currently.

The further aim is to get the integration to look at the last 7 days usage create a averge between certain times and ensure capacity during peak usage times almost like AI but im not that cleaver! 

The octopus integration has been moved from local api calls for each sensor to one global dictionary this means the data will be easily accessable for all future addons.

to install just copy the contents to your custom_components folder, with the folder name battery_automation
Restart HA and then enter your API key and account number for octopus, this will find your tariff and then show you the rates for you personally. 

Due to the naming convention used within the integration you might not want to use this and Bottlecap Daves sensor. you might lose the sensors unless you rename them. 
