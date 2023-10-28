import './App.css';
import creds from "./credentials"

//data being read through creds can be hidden using dotenv later
function App() {
  let SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
  //call on authUrl to let user give app auth to read his gmail account's mails
  const handleRequest = ()=>{
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${creds.client_id}&redirect_uri=${creds.redirect_uris}&response_type=code&scope=${SCOPES}&access_type=offline&prompt=consent`;
    window.location.href = authUrl
  }
  return (
    <div className="App">
      <h1>Welcome to Email Parser</h1>
      <span>Do you wish to let us get data from your bank statements ? </span>
      <button onClick={handleRequest}>Yes</button>
    </div>
  );
}

export default App;
