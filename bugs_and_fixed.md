Okay some general bugs and fixes you have to do in this prompt feneratpr. 
ensure you dont ruin anything 
ensure everything hoew data gets stored and which fields gets stored remains constans and as it is how it., 
If need you must specifically ask me how you will approch that case. 

now bugs are: 
1. Edit prompt button for both ai prompt and system prompt
currently thre is no edit option for ai prompt or system prompt when generated, add edit icon and edit functionality where yser can edit and save the prompt. updated prompt will be set, alkso add undo redo option when changing prompt. so 3 cions, fit it correctly in final prompt window and make it functional. 

2. Synonyms support in system_prompt
Add a synonym option at top, on clickin which a table will appear with synonyms, store this synonyms in JSON field and always carry it. user can edit and update this synonyms, its just a dictionary with words with mutliple meanisn and domain naems will be stored there. 
where this synonyms ,must be used: 
it should be referred when a system prompt is generated. add it in such way or sentence formattring so that it makes meaning and helps system prompt to be strog using those sysnonys, you can fix templare in which sysnonyms if exists will be added. and the single wor which has synonyms, muct be there in system prompt, if in system prompt use that template snected to sthetngten system prompt or esle dont. 

3.  Wizard bug fixing 
There is always table prompt wizard like table placejlder and ll 
Table Column Header
Table Filters
Table Synonyms
Grouping Logic
Validation
this one, its always there, maybe its useful fpor table tab placeholders. but not for others like standard and all. 
so fix this UI bug.
also one UI bug is, generated rtesult lways showed in every tab. so keep it to that tab itself, if not saved it will be goned if closed the app. or esloe it will be there if user navigates, generated prompt should be visible. 

4. Other than tagle prompt , for othe rplaceholders than tbale prompt - add a field names Hint/Note
in which user will wirte ianything if must be taken care of or must be there in system primpt and all. 
this wont be stored in xlsx/data , but will bethere in real time aand used in system prompt. 
so make small field for this. 

5. PID prompt template has issue,s it wirtes metedata query prompt rather than specific drawing prompt. below is the drawing prompt which you can refer and make templatre for PID prompt. but ensure query must be alwys there. i.e @metadataQuery. 

for now write as simple, as the mechnism is it has very rnaodm text form drawing extract form the tiny part, so guesisng nd all should not be ther. ensure to focus on titny details, PID title, document number must be combines like this. 



6. currently there is no grouping feature. 
Add a new tag/tab like others as grouping. 
In that show all current saved ## placeholders from db and ask user to select from them to group. 
user selects and a button will be there to group selected tags. on clicking they will be grouped. means. 
for selected plaholders add a feild @grouoign wuth placeholder name. in their every prompt. 
example: @grouping=["[Analog input tag##]"\n"[ioadd##]"] this is how grouping tag works. 

[Analog Input Tag##]	N/A	@grouping=["[Analog input tag##]"\n"[ioadd##]"]\n<column_header> "Tag Name" </column_header>\n<filters> ("Signal type"!="Analog Input" | "table_header"="Analog Inputs") </filters>\n<synonyms>\n<synonym> "Signal type" | "Signal_type" </synonym>\n<synonym> "Analog input" | "Analog inputs" </synonym>\n</synonyms>	["IO List"]
[ioadd##]	N/A	@grouping=["[Analog input tag##]"\n"[ioadd##]"]\n<column_header> "FC IO" </column_header>\n<filters> ("Signal type"!="Analog Input" | "table_header"="Analog Inputs") </filters>\n<synonyms>\n<synonym> "Signal type" | "Signal_type" </synonym>\n<synonym> "Analog input" | "Analog inputs" </synonym>\n</synonyms>	["IO List"]
[ioadd2##]	N/A	@grouping=["[analog input2##]"\n"[ioadd2##]"]\n<column_header> "Monitored on steps" </column_header>\n<filters> ("Signal type"="SERIAL RS485" | "table_header"="Aborting alarms") </filters>\n<synonyms>\n<synonym> "Signal type" | "Signal_type" </synonym>\n<synonym> "Analog input" | "Analog inputs" </synonym>\n</synonyms>	["Alarm List"]
[analog input2##]	N/A	@grouping=["[analog input2##]"\n"[ioadd2##]"]\n<column_header> "Alarm Name" </column_header>\n<filters> ("Signal type"="SERIAL RS485" | "table_header"="Aborting alarms") </filters>\n<synonyms>\n<synonym> "Signal type" | "Signal_type" </synonym>\n<synonym> "Analog input" | "Analog inputs" </synonym>\n</synonyms>	["Alarm List"]
 
 like this see how it works. so do this, and update the db as well the prompt must be updated with grouping tag. 

also keep a search bar in this Goruping tab . 


