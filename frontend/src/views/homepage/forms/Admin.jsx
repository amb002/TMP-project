import React from 'react';

const Admin = () => {
  return (
    <div>
      <h2>Form 3</h2>
      <form>
        <label>
          Password:
          <input type="password" name="password" />
        </label>
        <br />
        <button type="submit">Submit</button>
      </form>
    </div>
  );
}

export default Admin;
