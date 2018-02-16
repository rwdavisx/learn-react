import React, { Component } from 'react';
import {MdEmail} from 'react-icons/lib/md';
import './message-button.css';

class MessageButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
        }
    };

    render() {
        return (
        <div className={'message-btn'}>
            <MdEmail />
        </div>
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default MessageButton;


