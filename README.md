# TEHIK - Ilmastiku mõju haiguste esinemisele

##### Analysis correlation between weather conditions and diagnoses

### Sisukord
1. [Andmeallikad](#andmeallikad)
2. [Arhitektuur](#arhitektuur)
3. [Andmestik](#andmestik)
4. [Andmekvaliteet](#andmekvaliteedi-testid)
5. [Stack](#stack)
6. [Käivitamine](#käivitamine)
7. [Saladused ja konfiguratsioon](#saladused-ja-konfiguratsioon)
8. [Projekti struktuur](#projekti-struktuur)
9. [Kokkuvõte](#kokkuvõte-puudused-ja-võimalikud-edasiarendused)
10. [Meeskond](#meeskond)

### Äriküsimus

Küsimus: **"Kuidas jaotuvad enim levinud diagnoosid piirkonniti ning kas esineb statistiliselt oluline seos vihmaste ilmastikutingimuste ja kroonilise valu või liigesevalu diagnooside sagenemise vahel?"**

Projekti eesmärk on uurida, kuidas jaotuvad diagnoosid piirkonniti ning kas vihmastel ilmastikutingimustel võib olla seos kroonilise valu või liigesevalu diagnooside sagedasema esinemisega. Selleks analüüsitakse, millised diagnoosid on erinevates piirkondades kõige levinumad, kui palju esineb kroonilise valu või liigesevalu diagnoosiga patsiente ning kas vihmastel päevadel on nende patsientide arv piirkonniti suurem. Lisaks võrreldakse piirkondade lõikes vihmaste päevade osakaalu, et hinnata, kas ilmastikutingimuste ja vaadeldavate diagnooside vahel võib esineda seos.

**Mõõdikud**
1. Kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti  
    Patsientide arv igas piirkonnas, kellel esineb kroonilise valu või liigesevaluga seotud diagnoos.
2. Vihmastel päevadel kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti  
    Patsientide arv piirkondades, kus kroonilise valu või liigesevalu diagnoosiga patsiendid langevad kokku vihmaste päevadega valitud perioodil.
3. Vihmaste päevade osakaal piirkonniti (%)
4. Kas haiguste ägenemist mõjutab pigem vihm?
5. Kas temperatuuril või muudel teguritel on mingi mõju?

### Andmeallikad
1. Ilmastikuandmete API
2. WHO rahvusvaheliste haiguste klassifikaator  - [ICD-10](https://icd.who.int/icdapi)
3. Sünteetilised terviseandmed HL7 FHIR andmevahetusstandardis [Synthea](https://github.com/synthetichealth/synthea)

### Arhitektuur
Arhitektuuri dokumentatsioon on koostatud mermaid diagrammi kasutades. 
Kujutatud on andmevoogu, kuidas andmete sissevõtt toimub ning kuidas transformatsioonidega on jõutud ärikihini. 
Projekti andmed oleme üles ehitanud täheskeemi põhimõttel, kus konteksti oleme toonud dimensiooni tabelitesse ja faktid faktitabelitesse. 

Projekti arhitektuur kujuneb [siin](arhitektuur.md)  


### Andmestik

| Allikas | Tüüp | Ajas muutuv? | Roll |
|---------|------|--------------|------|
| Ilmastikuandmed | [API ] | Jah, [iga tund / päevas / muu] | Põhiandmevoog |
| WHO rahvusvaheliste haiguste klassifikaator | API | Ei, staatiline | Kõrvaltabel |
| Sünteetilised terviseandmed | [seed / dim-tabel] | Ei, staatiline | Kõrvaltabel |


### Andmekvaliteedi testid

### Stack

| Komponent | Tööriist |
|-----------|---------|
| Sissevõtt | [Python / Airflow / muu] |
| Transformatsioon | [SQL / dbt / muu] |
| Andmehoidla | PostgreSQL |
| Näidikulaud | [Superset / Streamlit / muu] |
| Orkestreerimine | [Airflow / cron / muu] |

### Käivitamine

### Saladused ja konfiguratsioon

### Projekti struktuur

### Kokkuvõte, puudused ja võimalikud edasiarendused 

**Kokkuvõte:**
- [Loetle, mis on lõpule viidud, mis töötab hästi]

**Puudused:**
- [Loetle ausalt, mis jäi tegemata - see ei mõjuta hinnet negatiivselt, vaid aitab hinnata]

**Mis edasi:**
- [Mida tahaksid edasi teha, kui aega oleks rohkem]

### Meeskond

| Nimi | Roll |
|------|------|
| Sergei Erbin | [Roll] |
| Maria Kuusik | [Roll] |
| Kalder Maarand | [Roll] |
| Scharlett Hansson | [Roll] |
