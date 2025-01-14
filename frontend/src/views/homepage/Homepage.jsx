import React, { useState } from 'react';
import Button from '@mui/material/Button';
import Admin from './forms/Admin';
import Login from './forms/Login';
import Register from './forms/Register';
import DeleteFingerprint from './forms/Delete';

function Homepage() {
    const [formNumber, setFormNumber] = useState(null);

    const handleClick = (buttonNumber) => {
        setFormNumber(buttonNumber);
    };

    const renderForm = () => {
        switch (formNumber) {
            case 1:
                return <Register />;
            case 2:
                return <Login />;
            case 3:
                return <Admin />;
            case 4:
                return <DeleteFingerprint />
            default:
                return null;
        }
    };

    return (
        <div style={{ textAlign: 'center', marginTop: '50px' }}>
            <h1>Welcome to our company!</h1>
            <p>Identification check:</p>
            <div>
                <Button variant="contained" color="primary" onClick={() => handleClick(1)} style={buttonStyle}>Register</Button>
                <Button variant="contained" color="secondary" onClick={() => handleClick(2)} style={buttonStyle}>Authenticate</Button>
                <Button variant="contained" color="success" onClick={() => handleClick(3)} style={buttonStyle}>Informations</Button>
                <Button variant="contained" color="error" onClick={() => handleClick(4)} style={buttonStyle}>Delete</Button>
            </div>
            <div style={{ marginTop: '20px' }}>
                {renderForm()}
            </div>
        </div>
    );
}

const buttonStyle = {
    margin: '10px',
    padding: '10px 20px',
    fontSize: '16px',
    cursor: 'pointer',
};

export default Homepage;
