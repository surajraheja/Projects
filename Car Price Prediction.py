import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score


dataset = pd.read_csv("data/dataset.csv")      #reading the data.
dataset.head(5)

X_train, X_test, y_train, y_test = train_test_split(dataset.iloc[:, :-1], 
                                                    dataset.iloc[:, -1],        #spliting the data into test and train dataset.
                                                    test_size = 0.3, 
                                                    random_state = 42)

X_train.info()              #information or data for training dataset.

X_train = X_train.iloc[:, 1:]
X_test = X_test.iloc[:, 1:]

X_train["Name"].value_counts()

make_train = X_train["Name"].str.split(" ", expand = True)
make_test = X_test["Name"].str.split(" ", expand = True)

X_train["Manufacturer"] = make_train[0]
X_test["Manufacturer"] = make_test[0]

plt.figure(figsize = (12, 8))
plot = sns.countplot(x = 'Manufacturer', data = X_train)               #checking and confirming of no null values and identity all unique values.
plt.xticks(rotation = 90)
for p in plot.patches:
    plot.annotate(p.get_height(), 
                        (p.get_x() + p.get_width() / 2.0, 
                         p.get_height()), 
                        ha = 'center', 
                        va = 'center', 
                        xytext = (0, 5),
                        textcoords = 'offset points')
plt.title("Count of cars based on manufacturers")
plt.xlabel("Manufacturer")
plt.ylabel("Count of cars")

X_train.drop("Name", axis = 1, inplace = True)
X_test.drop("Name", axis = 1, inplace = True)                 

X_train.drop("Location", axis = 1, inplace = True)            
X_test.drop("Location", axis = 1, inplace = True)

curr_time = datetime.datetime.now()
X_train['Year'] = X_train['Year'].apply(lambda x : curr_time.year - x)         # For the time and the year.
X_test['Year'] = X_test['Year'].apply(lambda x : curr_time.year - x)

X_train["Kilometers_Driven"]

mileage_train = X_train["Mileage"].str.split(" ", expand = True)               # For mileage.
mileage_test = X_test["Mileage"].str.split(" ", expand = True)
X_train["Mileage"] = pd.to_numeric(mileage_train[0], errors = 'coerce')
X_test["Mileage"] = pd.to_numeric(mileage_test[0], errors = 'coerce')

print(sum(X_train["Mileage"].isnull()))
print(sum(X_test["Mileage"].isnull()))               # Checking for missing values.

X_train["Mileage"].fillna(X_train["Mileage"].astype("float64").mean(), inplace = True)    #there is always a missing value then replacing it with mean value.
X_test["Mileage"].fillna(X_train["Mileage"].astype("float64").mean(), inplace = True) 



cc_train = X_train["Engine"].str.split(" ", expand = True)
cc_test = X_test["Engine"].str.split(" ", expand = True)                 # For engine, power and seat. 
X_train["Engine"] = pd.to_numeric(cc_train[0], errors = 'coerce')
X_test["Engine"] = pd.to_numeric(cc_test[0], errors = 'coerce')
bhp_train = X_train["Power"].str.split(" ", expand = True)
bhp_test = X_test["Power"].str.split(" ", expand = True)



X_train["Power"] = pd.to_numeric(bhp_train[0], errors = 'coerce')
X_test["Power"] = pd.to_numeric(bhp_test[0], errors = 'coerce')
X_train["Engine"].fillna(X_train["Engine"].astype("float64").mean(), inplace = True)
X_test["Engine"].fillna(X_train["Engine"].astype("float64").mean(), inplace = True)
X_train["Power"].fillna(X_train["Power"].astype("float64").mean(), inplace = True)
X_test["Power"].fillna(X_train["Power"].astype("float64").mean(), inplace = True)
X_train["Seats"].fillna(X_train["Seats"].astype("float64").mean(), inplace = True)
X_test["Seats"].fillna(X_train["Seats"].astype("float64").mean(), inplace = True)


X_train.drop(["New_Price"], axis = 1, inplace = True)               # New Price.
X_test.drop(["New_Price"], axis = 1, inplace = True)


X_train = pd.get_dummies(X_train,
                         columns = ["Manufacturer", "Fuel_Type", "Transmission", "Owner_Type"],
                         drop_first = True)
X_test = pd.get_dummies(X_test,                                                                # Data Processing.
                         columns = ["Manufacturer", "Fuel_Type", "Transmission", "Owner_Type"],
                         drop_first = True)


missing_cols = set(X_train.columns) - set(X_test.columns)
for col in missing_cols:
    X_test[col] = 0
X_test = X_test[X_train.columns]

standardScaler = StandardScaler()
standardScaler.fit(X_train)
X_train = standardScaler.transform(X_train)
X_test = standardScaler.transform(X_test)

linearRegression = LinearRegression()
linearRegression.fit(X_train, y_train)         # Training and Pridicting.
y_pred = linearRegression.predict(X_test)
r2_score(y_test, y_pred)

rf = RandomForestRegressor(n_estimators = 100)
rf.fit(X_train, y_train)
y_pred = rf.predict(X_test)
r2_score(y_test, y_pred)