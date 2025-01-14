import React, { useState } from "react";
import axios from "axios";

const RegisterFingerprint = () => {
  const [id, setId] = useState("");
  const [alias, setAlias] = useState("");
  const [message, setMessage] = useState("");

  const handleRegister = async () => {
    try {
      const response = await axios.post("http://127.0.0.1:8000/enroll", {
        id: parseInt(id),
        alias,
      });
      setMessage(`Success: ${response.data.message}`);
    } catch (error) {
      if (error.response) {
        setMessage(`Error: ${error.response.data.detail}`);
      } else {
        setMessage(`Error: ${error.message}`);
      }
    }
  };

  return (
    <div>
      <h1>Register Fingerprint</h1>
      <input
        type="number"
        placeholder="Enter Fingerprint ID"
        value={id}
        onChange={(e) => setId(e.target.value)}
      />
      <input
        type="text"
        placeholder="Enter Alias"
        value={alias}
        onChange={(e) => setAlias(e.target.value)}
      />
      <button onClick={handleRegister}>REGISTER</button>
      {message && <p>{message}</p>}
    </div>
  );
};

export default RegisterFingerprint;
