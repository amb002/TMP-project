import React, { useState } from "react";
import axios from "axios";

const DeleteFingerprint = () => {
  const [fingerprintId, setFingerprintId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleDelete = async () => {
    setMessage("");
    setError("");

    if (!fingerprintId) {
      setError("Please enter a valid fingerprint ID.");
      return;
    }

    try {
      const response = await axios.delete(`http://localhost:8000/fingerprint/${fingerprintId}`);
      setMessage(response.data.message);
      setFingerprintId("");
    } catch (err) {
      setError(err.response?.data?.detail || "An error occurred while deleting the fingerprint.");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Delete Fingerprint</h1>
      <div>
        <input
          type="number"
          value={fingerprintId}
          onChange={(e) => setFingerprintId(e.target.value)}
          placeholder="Enter Fingerprint ID"
          style={{ padding: "10px", marginRight: "10px", width: "300px" }}
        />
        <button onClick={handleDelete} style={{ padding: "10px" }}>
          Delete
        </button>
      </div>

      {error && <p style={{ color: "red", marginTop: "20px" }}>{error}</p>}
      {message && <p style={{ color: "green", marginTop: "20px" }}>{message}</p>}
    </div>
  );
};

export default DeleteFingerprint;
