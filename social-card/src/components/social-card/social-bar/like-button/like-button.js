import React, { Component } from 'react';
import { FaHeart } from 'react-icons/lib/fa';

import './like-button.css';

class LikeButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
        }
    };

    render() {
        return (
            <FaHeart className={'like-button'} onClick={this.handleComment('like')} />
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default LikeButton;
