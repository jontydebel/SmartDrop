// Import necessary modules
const express = require('express');
const path = require('path');
const bodyParser = require('body-parser');
const { MongoClient } = require('mongodb');

// Create Express app
const app = express();
const port = 8081;
const mongoUrl = 'mongodb://localhost:27017';
const dbName = 'smartDropData';

// MongoDB client
const client = new MongoClient(mongoUrl);

let latestLidStatusAction = 'Not yet set'

// Middleware
app.set('trust proxy', 'loopback');
app.use(bodyParser.json());

// Connect to MongoDB
client.connect()
  .then(() => {
    console.log('Connected to MongoDB');
  })
  .catch(err => {
    console.error('Error connecting to MongoDB:', err);
  });

// Function to insert data into MongoDB
async function insertDataIntoMongoDB(collectionName, data) {
  try {
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    const result = await collection.insertMany(data);
    console.log('Inserted documents into MongoDB');
    return result;
  } catch (error) {
    console.error('Error inserting data into MongoDB:', error);
    throw error;
  }
}

// Function to retrieve data from MongoDB
async function fetchDataFromMongoDB(collectionName) {
  try {
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    const data = await collection.find({}).sort({ timestamp: 1 }).toArray(); // Sort by timestamp in ascending order
    return data;
  } catch (error) {
    console.error('Error fetching data from MongoDB:', error);
    throw error;
  }
}

// Function to retrieve data from MongoDB
async function fetchFilteredDataFromMongoDB(collectionName) {
  try {
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    // Use $not and $regex to exclude entries with timestamps containing "-"
    const data = await collection.find({ 
      $and: [ 
        { timestamp: { $exists: false } },  // Exclude entries with timestamp
        { timestamp: { $not: { $regex: /^.*-.*$/ } } }, // Exclude entries with timestamp containing a hyphen
        { date: { $not: { $regex: /^.*-.*$/ } } }, // Exclude entries with date containing a hyphen
        { waterLevel: { $ne: -1 } }, // Exclude entries with waterLevel equal to -1
        { hours: { $eq: -1 } } // Exclude entries with waterLevel equal to -1
      ]
    }).toArray();
    return data;
  } catch (error) {
    console.error('Error fetching data from MongoDB:', error);
    throw error;
  }
}

// Function to retrieve data from MongoDB
async function fetchCurrentLevelDataFromMongoDB(collectionName) {
  try {
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    // Use $not and $regex to exclude entries with timestamps containing "-"
    const data = await collection.find({ 
      currentLevel: { $ne: -1 } // Exclude entries with waterLevel equal to -1
    }).toArray();
    return data;
  } catch (error) {
    console.error('Error fetching data from MongoDB:', error);
    throw error;
  }
}

// Function to retrieve data from MongoDB
async function fetchTimeDataFromMongoDB(collectionName) {
  try {
    const db = client.db(dbName);
    const collection = db.collection(collectionName);
    // Use $not and $regex to exclude entries with timestamps containing "-"
    const data = await collection.find({ 
      $and: [ 
        { timestamp: { $exists: false } },  // Exclude entries with timestamp
        //{ timestamp: { $not: { $regex: /^.*-.*$/ } } }, // Exclude entries with timestamp containing a hyphen
        { date: { $not: { $regex: /^.*-.*$/ } } }, // Exclude entries with date containing a hyphen
        // { waterLevel: { $ne: -1 } }, // Exclude entries with waterLevel equal to -1
        { hours: { $ne: -1 } } // Exclude entries with waterLevel equal to -1
      ]
    }).toArray();
    return data;
  } catch (error) {
    console.error('Error fetching data from MongoDB:', error);
    throw error;
  }
}

// Routes
// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// GET route to fetch data from MongoDB for dashboard
app.get('/api/dashboard', async (req, res) => {
  try {
    // Fetch data for the dashboard
    const tankData = await fetchFilteredDataFromMongoDB('tankData');
    const latestCurrentLevelData = await fetchCurrentLevelDataFromMongoDB('currentLevelData');
    const latestLidStatusData = await fetchDataFromMongoDB('lidStatusData');
    const timeOpenData1 = await fetchTimeDataFromMongoDB('tankData');

    // Sort tankData by timestamp in descending order
    tankData.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    // Get the 10 latest entries from tankData
    // const latestTankData = tankData.slice(0, 14);
    const latestTankData = tankData;
    
    // Get the latest current tank level entry
    const latestCurrentLevel = latestCurrentLevelData[latestCurrentLevelData.length - 1];
    
    // Get the latest lid status entry
    const latestLidStatus = latestLidStatusData[latestLidStatusData.length - 1];

    const timeOpenData = timeOpenData1.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    // Return all the data to the dashboard
    res.json({ latestTankData, latestCurrentLevel, latestLidStatus, timeOpenData });
  } catch (error) {
    console.error('Error handling GET request:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// POST route to receive tank data and insert into MongoDB
app.post('/api/tankData', async (req, res) => {
  try {
    const requestData = req.body;
    await insertDataIntoMongoDB('tankData', requestData);
    console.log('Inserted tank data into MongoDB:', requestData);
    res.json({ message: 'Tank data received and inserted successfully' });
  } catch (error) {
    console.error('Error handling tank data POST request:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// POST route to receive current tank level data and insert into MongoDB
app.post('/api/currentLevelData', async (req, res) => {
  try {
    const requestData = req.body;
    await insertDataIntoMongoDB('currentLevelData', requestData);
    console.log('Inserted current tank level data into MongoDB:', requestData);
    res.json({ message: 'Current tank level data received and inserted successfully' });
  } catch (error) {
    console.error('Error handling current tank level data POST request:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// POST route to receive lid status data and insert into MongoDB
app.post('/api/lidStatusData', async (req, res) => {
  try {
    const requestData = req.body;
    await insertDataIntoMongoDB('lidStatusData', requestData);
    console.log('Inserted lid status data into MongoDB:', requestData);
    res.json({ message: 'Lid status data received and inserted successfully' });
  } catch (error) {
    console.error('Error handling lid status data POST request:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// GET route to fetch the latest lid status action
app.get('/api/latestLidStatusAction', (req, res) => {
  try {
    // Send the latest lid status action as response
    res.json({ action: latestLidStatusAction });
  } catch (error) {
    console.error('Error handling GET request for latest lid status action:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});

// POST route to handle toggling lid status
app.post('/api/toggleLidStatus', async (req, res) => {
  try {
    const { action } = req.body;
    let message = '';

    // Store the latest action
    latestLidStatusAction = action;


    if (action === 'open') {
      // Logic to handle opening the lid
      // You can insert data into MongoDB or perform any other necessary actions
      message = 'Lid opened successfully';
    } else if (action === 'close') {
      // Logic to handle closing the lid
      // You can insert data into MongoDB or perform any other necessary actions
      message = 'Lid closed successfully';
    } else if (action === 'reset') {
      // Logic to handle resetting the lid
      // You can insert data into MongoDB or perform any other necessary actions
      message = 'Lid status reset successfully';
    } else {
      return res.status(400).json({ error: 'Invalid action' });
    }

    // Send response back to the client
    res.json({ message });
  } catch (error) {
    console.error('Error handling toggle lid status POST request:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
});


// Start the server
app.listen(port, () => console.log(`App listening on port ${port}`));
