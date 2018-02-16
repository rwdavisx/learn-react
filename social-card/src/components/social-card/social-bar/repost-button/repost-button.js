import React, { Component } from 'react';
import { FaRepeat } from 'react-icons/lib/fa';

import './repost-button.css';

class RepostButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
        }
    };

    render() {
        return (
            <FaRepeat className={'repost-button'} onClick={this.handleComment('repost')} />
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default RepostButton;
