# Arhitektuuri dokumentatsioon
1.[Andmeallikad](#andmeallikad)
2.[Andmevoo skeem](#andmevoo-skeem)
3.[ER-diagramm](#täheskeemi-realisatsioon-er-diagrammina)

Skeemid on loodud Mermaidi süntaksis. Et näha neid graafilisel kujul otse VS Code'is, on soovitatav kasutada Mermaid Editor või Markdown Preview Mermaid Support laiendust.

## Andmeallikad
```mermaid
%% Andmeallikad

graph LR
    subgraph Andmeallikad
        A[Synthea andmestik] 
        B[WHO ICD-10 API<br/>või<br/>TEHIK Terminoloogiaserver]
        C[Ilmaandmete API]
    end

    subgraph Puhastuskiht
        D[(PATIENT)]
        E[(DIAGNOSE)]
        F[(LOCATION)]
        G[(ICD-10)]
        H[(WEATHER)]
    end

    A --> D
    A --> E
    A --> F
    
    B --> G

    C --> H
```

## Andmevoo skeem
Andmevoo skeemis eristatakse andmetoru jaoks kolme kihti: toorkiht, puhastuskiht ning ärikiht

```mermaid
%% Andmevoo vooskeem

flowchart LR

    %% =========================
    %% ALGALLIKAD
    %% =========================
    A[Synthea terviseandmed]
    A1[patients]
    A2[conditions]
    A3[encounters]
    A4[demograafilised andmed]

    B1[Rahvusvaheline haiguste klassifikaator / WHO ICD-10]

    C[Ilmavaatluse API]
    C1[sademed]
    C2[temperatuur]
    C3[õhuniiskus]
    C4[õhurõhk]

    A --> A1
    A --> A2
    A --> A3
    A --> A4

    C --> C1
    C --> C2
    C --> C3
    C --> C4

    %% =========================
    %% TOORKIHT / PRONKS KIHT
    %% =========================
    D[TOORKIHT]

    A1 --> D
    A2 --> D
    A3 --> D
    A4 --> D
    B1 --> D
    C1 --> D
    C2 --> D
    C3 --> D
    C4 --> D

    E1[raw_patients]
    E2[raw_conditions]
    E3[raw_encounters]
    E4[raw_icd10]
    E5[raw_weather]
    E6[raw_countries, regions]

    D --> E1
    D --> E2
    D --> E3
    D --> E4
    D --> E5
    D --> E6

    %% =========================
    %% PUHASTUSKIHT / HÕBE KIHT
    %% =========================
    F[(PUHASTUSKIHT)]
    F1[kuupäevade ühtlustamine]
    F2[piirkondade seostamine]
    F3[diagnooside standardiseerimine/valideerimine ICD-10 abil]
    F4[kroonilise valu ja liigesevalu diagnooside filtreerimine]
    F5[vihmaste päevade märgistamine]

    E1 --> F
    E2 --> F
    E3 --> F
    E4 --> F
    E5 --> F

    F --> F1
    F --> F2
    F --> F3
    F --> F4
    F --> F5

    %% =========================
    %% ÄRIKIHT / KULD KIHT
    %% =========================
    G[(ÄRIKIHT)]
    G1[dim_region]
    G2[dim_diagnosis]
    G3[dim_date]
    G4[fact_diagnosis_region]
    G5[fact_weather_region_day]
    G6[fact_pain_weather_analysis]

    F1 --> G
    F2 --> G
    F3 --> G
    F4 --> G
    F5 --> G

    G --> G1
    G --> G2
    G --> G3
    G --> G4
    G --> G5
    G --> G6

    %% =========================
    %% ANDMEKVALITEET
    %% =========================
    H[Andmekvaliteedi testid]
    H1[not null]
    H2[unique]
    H3[väärtuste vahemik]
    H4[referentsseosed]
    H5[duplikaatide kontroll]

    G --> H 

    H --> H1
    H --> H2
    H --> H3
    H --> H4
    H --> H5

    %% =========================
    %% ANALÜÜTIKA / VISUAALID
    %% =========================
    I[ANALÜÜTIKA]
    I1[KPI 1<br/>kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti]
    I2[KPI 2<br/>vihmastel päevadel kroonilise valu või liigesevalu diagnoosiga patsientide arv piirkonniti]
    I3[KPI 3<br/>vihmaste päevade osakaal piirkonniti]
    I4[Lisavisuaal<br/>enimlevinud diagnoosid piirkonniti]

    G1 --> I
    G2 --> I
    G3 --> I
    G4 --> I
    G5 --> I
    G6 --> I

    I --> I1
    I --> I2
    I --> I3
    I --> I4
```

## Täheskeemi realisatsioon ER-diagrammina

```mermaid
---
title: Toorkihist puhastuskihi ER-diagramm
---
erDiagram
    PATIENT ||--o{ DIAGNOSE : gets
    DIAGNOSE ||--|{ ICD-10 : contains
    PATIENT }|..|{ LOCATION : uses
    LOCATION ||--o{ WEATHER : has
```