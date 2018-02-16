import React, { Component } from 'react';
import { FaEnvelope } from 'react-icons/lib/fa';

import './message-button.css';

class MessageButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
        }
    };

    render() {
        return (
            <FaEnvelope className={'message-button'} onClick={this.handleComment('message')} />
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default MessageButton;


