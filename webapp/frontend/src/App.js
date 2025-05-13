// frontend/src/App.js
import React, { useEffect, useState } from 'react';

function App() {
  const [listings, setListings] = useState([]);

  useEffect(() => {
    fetch('/api/listings/')
      .then(response => response.json())
      .then(data => setListings(data))
      .catch(error => console.error('Error fetching data:', error));
  }, []);

  return (
    <div className="App">
      <h1>Listings</h1>
      <ul>
        {listings.map(listing => (
          <li key={listing.id}>
            <strong>ID:</strong> {listing.id} <br />
            <strong>Data:</strong> {listing.data} <br />
            <strong>Inserted At:</strong> {listing.inserted_at}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;