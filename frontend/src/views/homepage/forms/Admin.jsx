import React, { useState } from "react";
import axios from "axios";

const MatchList = () => {
  const [alias, setAlias] = useState("");
  const [matches, setMatches] = useState([]);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    setError("");
    setMatches([]);

    try {
      const response = await axios.get(`http://localhost:8000/matches/${alias}`);
      setMatches(response.data.matches);
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Search Matches by Alias</h1>
      <div>
        <input
          type="text"
          value={alias}
          onChange={(e) => setAlias(e.target.value)}
          placeholder="Enter alias"
          style={{ padding: "10px", marginRight: "10px", width: "300px" }}
        />
        <button onClick={handleSearch} style={{ padding: "10px" }}>
          Search
        </button>
      </div>

      {error && <p style={{ color: "red", marginTop: "20px" }}>{error}</p>}

      {matches.length > 0 && (
        <div style={{ marginTop: "20px" }}>
          <h2>Matches for Alias: {alias}</h2>
          <table border="1" style={{ width: "100%", marginTop: "10px", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th>Fingerprint ID</th>
                <th>Match ID</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {matches.map((match, index) => (
                <tr key={index}>
                  <td>{match.fingerprint_id}</td>
                  <td>{match.match_id}</td>
                  <td>{match.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default MatchList;
