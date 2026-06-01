const { MongoClient } = require('mongodb');

const uri = "mongodb+srv://bsnoeijer_db_user:V04xyd8eFa6XmXDQ@cluster0.44jalqh.mongodb.net/?appName=Cluster0";

const client = new MongoClient(uri);

async function run() {
  try {
    await client.connect();
    console.log("Connected to MongoDB");
    // Add your database operations here
  } finally {
    await client.close();
  }
}

run().catch(console.dir);