import React, { Component } from 'react';
import { FaCommentO } from 'react-icons/lib/fa';

import './comment-button.css';

class CommentButton extends Component {
    constructor(props) {
        super(props);
        this.state = {
        }
    };

    render() {
        return (
            <FaCommentO className={'comment-button'} onClick={this.handleComment('comment')} />
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default CommentButton;
