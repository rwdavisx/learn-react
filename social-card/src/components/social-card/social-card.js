import React, { Component } from "react";
import "./social-card.css";

import ContentBar from "./content-bar/content-bar";
import ExternalBox from "./external-box/external-box";
import SocialBar from "./social-bar/social-bar";

class SocialCard extends Component {
  constructor(props) {
    super(props);
    this.state = {
      userName: this.props.userName,
      fullName: this.props.fullName,
      date: this.props.date,
      text: this.props.text,
      externalLink: this.props.externalLink
    };
  }

  render() {
    return (
      <div className="container-fluid col-12 col-md-8 col-lg-6 p-2 border-bottom">
        <ContentBar
          userId={this.state.userName}
          fullName={this.state.fullName}
          date={this.state.date}
          text={this.state.text}
        />
        <ExternalBox input={this.state.externalLink} />
        <div className={'col-6 offset-2'}>
          <SocialBar />
        </div>
      </div>
    );
  }

  giveComment(input) {
    return function () {
      console.log(input);
    };
  }
}

export default SocialCard;
