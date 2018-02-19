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
      <div className="container-fluid p-2 border-bottom">
        <div className={'row justify-content-center'}>
          <div className={'col-xl-6 col-lg-10 col-md-12 col-sm-10 col-xs-12'}>
            <div className={'container-fluid'}>
              <div className={'row justify-content-center'}>
                <div className={'col-12'}>
                  <ContentBar
                    userId={this.state.userName}
                    fullName={this.state.fullName}
                    date={this.state.date}
                    text={this.state.text} />
                </div>
              </div>
              <div className={'row'}>
                <div className={'col-10 offset-2'}>
                  <ExternalBox
                    input={this.state.externalLink} />
                </div>
              </div>

              <div className={'row'}>
                <div className={'col-6 offset-2'}>
                  <SocialBar />
                </div>
              </div>
            </div>
          </div>
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
