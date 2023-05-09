import React, { useState } from 'react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const response = await fetch(`http://127.0.0.1:8000/query/?query=${query}`);
    const data = await response.json();
    
    // var items = Object.keys(data).map(function(key) {
    //   return [key, data[key]];
    // })

    // var sortedResults = items.sort(function(first, second) {
    //   return second[1][0] - first[1][0];
    // });
    
    setResults(data);
  };

  const handleChange = (event) => {
    setQuery(event.target.value);
  };


  return (
    <div className="App">
      <form onSubmit={handleSubmit}>
        <label>
          Search:
          <input type="text" value={query} onChange={handleChange} />
        </label>
        <button type="submit">Submit</button>
      </form>
        <div className="results">
        {results.map((result, index) => (
          <div key={index}>
            {Object.entries(result).map(([key, value]) => (
              <div key={key}>
                <p>{key}:</p>
                <ul>
                  {value.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;


//   return (
//     <div className="App">
//       <form onSubmit={handleSubmit}>
//         <label>
//           Search:
//           <input type="text" value={query} onChange={handleChange} />
//         </label>
//         <button type="submit">Submit</button>
//       </form>
//         <div className="results">
//         {results.map((result, index) => (
//           <div key={index}>
//             {Object.entries(result).map(([key, value]) => (
//               <div key={key}>
//                 <p>{key}: {value}</p>
//               </div>
//             ))}
//           </div>
//         ))}
//       </div>
//     </div>
//   );
// }