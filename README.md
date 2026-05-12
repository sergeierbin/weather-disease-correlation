# Kuidas jaotuvad enim levinud diagnoosid piirkonniti ning kas esineb statistiliselt oluline seos vihmaste ilmastikutingimuste ja kroonilise valu või liigesevalu diagnooside sagenemise vahel?

##### Analysis correlation between weather conditions and diagnoses

### Sisukord
1. [Andmeallikad](#andmeallikad)
2. [Arhitektuur](#arhitektuur)
3. [Andmekvaliteet](#andmekvaliteet)
4. [Analüütika](#kpi-d)
5. [Juhised käivitamiseks](#juhised-käivitamiseks)

Projekti eesmärk on uurida, kuidas jaotuvad diagnoosid piirkonniti ning kas vihmastel ilmastikutingimustel võib olla seos kroonilise valu või liigesevalu diagnooside sagedasema esinemisega. Selleks analüüsitakse, millised diagnoosid on erinevates piirkondades kõige levinumad, kui palju esineb kroonilise valu või liigesevalu diagnoosiga patsiente ning kas vihmastel päevadel on nende patsientide arv piirkonniti suurem. Lisaks võrreldakse piirkondade lõikes vihmaste päevade osakaalu, et hinnata, kas ilmastikutingimuste ja vaadeldavate diagnooside vahel võib esineda seos.

### Andmeallikad
1. Ilmastikuandmete API
2. WHO rahvusvaheliste haiguste klassifikaator  - [ICD-10](https://icd.who.int/icdapi)
3. Sünteetilised terviseandmed HL7 FHIR andmevahetusstandardis [Synthea](https://github.com/synthetichealth/synthea)

### Arhitektuur
Projekti arhitektuur kujuneb [siin](arhitektuur.md)  
Kasutame seda ja toda ja transformeerime need ja need kokku. 

### Andmekvaliteet

### KPI-d
1. Kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti  
    Patsientide arv igas piirkonnas, kellel esineb kroonilise valu või liigesevaluga seotud diagnoos.
2. Vihmastel päevadel kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti  
    Patsientide arv piirkondades, kus kroonilise valu või liigesevalu diagnoosiga patsiendid langevad kokku vihmaste päevadega valitud perioodil.
3. Vihmaste päevade osakaal piirkonniti (%)
4. Kas haiguste ägenemist mõjutab pigem vihm?
5. Kas temperatuuril või muudel teguritel on mingi mõju?

### Juhised käivitamiseks
