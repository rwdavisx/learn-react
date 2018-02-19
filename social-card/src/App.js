import React, { Component } from 'react';
import logo from './logo.svg';
import './App.css';

import SocialCard from './components/social-card/social-card';
import { Card1, Card2 } from './db/sample-card';

class App extends Component {
  render() {
    return (
      <div className="App">
        <header className="App-header">
          <img src={logo} className="App-logo" alt="logo" />
          <h1 className="App-title">Welcome to SocialCard!</h1>
        </header>
        <SocialCard
          userName={Card1.userName}
          fullName={Card1.fullName}
          date={Card1.date}
          text={Card1.text}
          externalLink={Card1.externalLink}
        />
        <SocialCard
        userName={Card2.userName}
        fullName={Card2.fullName}
        date={Card2.date}
        text={Card2.text}
        externalLink={Card2.externalLink}
      />
      </div>
    );
  }
}

export default App;